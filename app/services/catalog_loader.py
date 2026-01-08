"""
Catalog Loader Service.
Handles complex ETL from OnixProduct (Pydantic) to Normalized DB Tables.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

# Models
from app.models.catalog import (
    CatalogProduct, Publisher, Contributor, CatalogProductContributor,
    Collection, CatalogProductCollection, CatalogTitle, CatalogLanguage,
    CatalogSubject, CatalogExtent, CatalogMeasure, CatalogAudienceRange,
    CatalogPrize, CatalogTextContent, CatalogRelatedProduct, CatalogPublishingDate,
    RefThemaSubject
)
from app.models.codes_v71 import (
    ProductIdentifierType, TitleType, ContributorRole, CollectionType,
    SubjectSchemeIdentifier, ProductRelation, DateType
)

THEMA_SCHEME_CODE = "93"  # ONIX List27 value for Thema
# Schemas
from app.schemas.onix_full import OnixProduct

class CatalogLoader:
    def __init__(self, session: AsyncSession, cache_ttl_seconds: int = 3600):
        self.session = session
        # Local caches within transaction scope to avoid repetitive DB lookups
        self._publisher_cache: Dict[str, UUID] = {}
        self._contributor_cache: Dict[str, UUID] = {} # Key: Normalized Name
        self._collection_cache: Dict[str, UUID] = {} # Key: Title
        self._thema_codes: Optional[set[str]] = None
        self._thema_cache_loaded_at: Optional[datetime] = None
        self._thema_cache_ttl = timedelta(seconds=cache_ttl_seconds)

    async def load_product(self, onix: OnixProduct) -> UUID:
        """
        Main entry point. Converts Pydantic ONIX -> DB CatalogProduct.
        Returns the Product UUID.
        """
        # 1. Resolve Identifiers
        isbn13 = self._extract_id(onix, ProductIdentifierType.ISBN_13)
        proprietary_id = onix.record_reference
        
        # 2. Check existence (Try ISBN first, then Reference)
        existing_product = await self._find_product(isbn13, proprietary_id)
        
        if existing_product:
            # Update logic (Simplified: we overwrite for now, or skip?)
            # For V3 migration, let's assume we update essential fields
            product = existing_product
            # self._update_core_fields(product, onix) # TODO: Implement updates
        else:
            product = CatalogProduct()
            self.session.add(product)
        
        # 3. Fill Core Fields
        product.record_reference = proprietary_id
        product.isbn_13 = isbn13
        product.ean = self._extract_id(onix, ProductIdentifierType.GTIN_13)
        product.sku = onix.extra.get("source_sku") if onix.extra else None
        
        product.product_form = onix.product_form
        # product.product_form_detail = ... # Need extraction logic
        
        product.onix_full = onix.model_dump(mode='json') # Save full dump
        
        # 4. Publisher
        if onix.publisher:
            pub_name = onix.publisher[0].publisher_name
            if pub_name:
                product.publisher_id = await self._get_or_create_publisher(pub_name)

        await self.session.flush() # Generate ID if new
        
        # 5. Process Sub-Tables (Clear old if updating, or just add for new)
        # Note: For strict updates, we delete existing relations first (Enrichment).
        await self._clear_related_data(product.id)
        
        await self._process_titles(product.id, onix)
        await self._process_contributors(product.id, onix)
        await self._process_collections(product.id, onix)
        await self._process_subjects(product.id, onix)
        await self._process_details(product.id, onix) # Extents, Measures, Languages

        return product.id

    async def _clear_related_data(self, pid: UUID):
        """
        Deletes all child records for a product to allow clean re-insertion.
        """
        # Delete Titles
        await self.session.execute(delete(CatalogTitle).where(CatalogTitle.product_id == pid))
        
        # Delete Contributors Link
        await self.session.execute(delete(CatalogProductContributor).where(CatalogProductContributor.product_id == pid))
        
        # Delete Collections Link
        await self.session.execute(delete(CatalogProductCollection).where(CatalogProductCollection.product_id == pid))
        
        # Delete Subjects
        await self.session.execute(delete(CatalogSubject).where(CatalogSubject.product_id == pid))
        
        # Delete Languages
        await self.session.execute(delete(CatalogLanguage).where(CatalogLanguage.product_id == pid))
        
        # Delete Extents
        await self.session.execute(delete(CatalogExtent).where(CatalogExtent.product_id == pid))
        
        # Delete TextContent
        await self.session.execute(delete(CatalogTextContent).where(CatalogTextContent.product_id == pid))
        
        # Delete Measures (Missing in original plan, adding now)
        await self.session.execute(delete(CatalogMeasure).where(CatalogMeasure.product_id == pid))

    # --- Helpers ---

    def _extract_id(self, onix: OnixProduct, type_code: str) -> Optional[str]:
        for ident in onix.product_identifier:
            if ident.product_id_type == type_code:
                return ident.id_value
        return None

    async def _find_product(self, isbn13: str, ref: str) -> Optional[CatalogProduct]:
        if isbn13:
            stmt = select(CatalogProduct).where(CatalogProduct.isbn_13 == isbn13)
            res = await self.session.execute(stmt)
            p = res.scalar_one_or_none()
            if p: return p
        
        stmt = select(CatalogProduct).where(CatalogProduct.record_reference == ref)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def _get_or_create_publisher(self, name: str) -> UUID:
        if name in self._publisher_cache:
            return self._publisher_cache[name]
        
        stmt = select(Publisher).where(Publisher.name == name)
        res = await self.session.execute(stmt)
        pub = res.scalar_one_or_none()
        
        if not pub:
            pub = Publisher(name=name)
            self.session.add(pub)
            await self.session.flush()
            
        self._publisher_cache[name] = pub.id
        return pub.id

    async def _get_or_create_contributor(self, name: str) -> UUID:
        # Simple normalization
        clean_name = name.strip()
        if clean_name in self._contributor_cache:
            return self._contributor_cache[clean_name]

        stmt = select(Contributor).where(Contributor.name == clean_name)
        res = await self.session.execute(stmt)
        c = res.scalar_one_or_none()

        if not c:
            c = Contributor(name=clean_name)
            self.session.add(c)
            await self.session.flush()
        
        self._contributor_cache[clean_name] = c.id
        return c.id

    # --- Relation Processors ---

    async def _process_titles(self, pid: UUID, onix: OnixProduct):
        if not onix.title_detail: return
        for td in onix.title_detail:
            if not td.title_element: continue
            elem = td.title_element[0] # Assume main element
            
            t = CatalogTitle(
                product_id=pid,
                type=td.title_type,
                title_text=elem.title_text,
                subtitle=elem.subtitle
            )
            self.session.add(t)

    async def _process_contributors(self, pid: UUID, onix: OnixProduct):
        if not onix.contributor: return
        
        # Dedup sequence if needed, strict ONIX has explicit sequences
        seq = 1
        for c in onix.contributor:
            if not c.person_name: continue
            cid = await self._get_or_create_contributor(c.person_name)
            
            role = c.contributor_role[0] if c.contributor_role else ContributorRole.BY_AUTHOR
            
            link = CatalogProductContributor(
                product_id=pid,
                contributor_id=cid,
                role=role,
                sequence_number=seq
            )
            self.session.add(link)
            seq += 1

    async def _process_collections(self, pid: UUID, onix: OnixProduct):
        if not onix.collection: return
        for col in onix.collection:
            # Try to find title
            title = None
            if col.title_detail and col.title_detail[0].title_element:
                title = col.title_detail[0].title_element[0].title_text
            
            if not title: continue
            
            # Find/Create Collection
            if title in self._collection_cache:
                col_id = self._collection_cache[title]
            else:
                stmt = select(Collection).where(Collection.title == title)
                res = await self.session.execute(stmt)
                db_col = res.scalar_one_or_none()
                if not db_col:
                    db_col = Collection(title=title, type=col.collection_type)
                    self.session.add(db_col)
                    await self.session.flush()
                self._collection_cache[title] = db_col.id
                col_id = db_col.id

            # Link
            seq_num = None
            if col.collection_sequence:
                seq_num = col.collection_sequence[0].collection_sequence_number

            link = CatalogProductCollection(
                product_id=pid,
                collection_id=col_id,
                sequence_number=str(seq_num) if seq_num else None
            )
            self.session.add(link)

    async def _process_subjects(self, pid: UUID, onix: OnixProduct):
        if not onix.subject: return

        await self._ensure_thema_cache()

        for s in onix.subject:
            if str(s.subject_scheme_identifier) == THEMA_SCHEME_CODE:
                # Skip invalid THEMA codes to avoid dangling refs
                if self._thema_codes is not None and s.subject_code not in self._thema_codes:
                    continue
            sub = CatalogSubject(
                product_id=pid,
                scheme_identifier=s.subject_scheme_identifier,
                subject_code=s.subject_code,
                subject_heading_text=s.subject_heading_text
            )
            self.session.add(sub)

    async def refresh_thema_cache(self) -> None:
        """Force reload THEMA codes (active only) into cache."""
        stmt = select(RefThemaSubject.code).where(RefThemaSubject.is_active.is_(True))
        res = await self.session.execute(stmt)
        self._thema_codes = {row[0] for row in res.fetchall()}
        self._thema_cache_loaded_at = datetime.utcnow()

    async def _ensure_thema_cache(self) -> None:
        """Load THEMA cache if missing or expired."""
        now = datetime.utcnow()
        if self._thema_codes is not None and self._thema_cache_loaded_at is not None:
            if now - self._thema_cache_loaded_at < self._thema_cache_ttl:
                return
        await self.refresh_thema_cache()

    async def _process_details(self, pid: UUID, onix: OnixProduct):
        # Languages
        if onix.language:
            for l in onix.language:
                self.session.add(CatalogLanguage(
                    product_id=pid,
                    role=l.language_role,
                    code=l.language_code
                ))
        
        # Extents (Pages)
        if onix.extent:
            for e in onix.extent:
                self.session.add(CatalogExtent(
                    product_id=pid,
                    type=e.extent_type,
                    value=e.extent_value,
                    unit=e.extent_unit
                ))

        # Measures (Dimensions)
        if onix.measure:
            for m in onix.measure:
                self.session.add(CatalogMeasure(
                    product_id=pid,
                    type=m.measure_type,
                    measurement=m.measure_value,
                    unit_code=m.measure_unit_code
                ))

    async def _ensure_thema_cache(self):
        if self._thema_codes is not None:
            return

        stmt = select(RefThemaSubject.code)
        res = await self.session.execute(stmt)
        self._thema_codes = set(res.scalars().all())
