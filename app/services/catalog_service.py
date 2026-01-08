"""
Service Layer - Бізнес-логіка і маппінг ORM → DTO.

Бере дані з Repository, трансформує у DTO, накладає правила.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.product_repository import ProductRepository
from app.schemas import (
    ProductCardDTO,
    ProductDetailDTO,
    TitleDTO,
    ContributorDTO,
    SubjectDTO,
    CatalogSearchResponseDTO,
)
from app.models.enums import map_form_to_type, map_status


class CatalogService:
    """Бізнес-логіка каталогу."""
    
    def __init__(self, session: AsyncSession):
        self.repo = ProductRepository(session)
        self.session = session
    
    async def get_products_list(
        self,
        page: int = 1,
        limit: int = 20,
    ) -> CatalogSearchResponseDTO:
        """
        Отримати список активних товарів.
        
        Args:
            page: Номер сторінки (1-based)
            limit: Товарів на сторінку
        
        Returns:
            CatalogSearchResponseDTO з пагінацією
        """
        # Розрахувати offset
        offset = (page - 1) * limit
        
        # Витягнути з БД
        products, total = await self.repo.get_all(limit=limit, offset=offset)
        
        # Трансформувати у DTO
        items = [
            await self._to_product_card(product)
            for product in products
        ]
        
        return CatalogSearchResponseDTO(
            total=total,
            page=page,
            limit=limit,
            items=items,
        )
    
    async def get_product_detail(self, product_id: str) -> Optional[ProductDetailDTO]:
        """
        Отримати повну деталь товару.
        
        Args:
            product_id: UUID товара
        
        Returns:
            ProductDetailDTO або None
        """
        product = await self.repo.get_by_id(product_id)
        if not product:
            return None
        
        return await self._to_product_detail(product)
    
    async def search(
        self,
        query: Optional[str] = None,
        thema_code: Optional[str] = None,
        product_form: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> CatalogSearchResponseDTO:
        """
        Пошук товарів.
        
        Args:
            query: Текст для пошуку
            thema_code: THEMA код (Y, YF, YFB)
            product_form: ONIX форма (BB, BC, EA)
            page: Сторінка
            limit: На сторінку
        
        Returns:
            CatalogSearchResponseDTO
        """
        offset = (page - 1) * limit
        
        # Витягнути з БД
        products, total = await self.repo.search(
            query=query,
            thema_code=thema_code,
            product_form=product_form,
            limit=limit,
            offset=offset,
        )
        
        # Трансформувати
        items = [
            await self._to_product_card(product)
            for product in products
        ]
        
        return CatalogSearchResponseDTO(
            total=total,
            page=page,
            limit=limit,
            items=items,
        )
    
    # ===== PRIVATE MAPPERS =====
    
    async def _to_product_card(self, product) -> ProductCardDTO:
        """Маппінг ORM → ProductCardDTO."""
        # Отримати назву
        title = product.titles[0].title_text if product.titles else "—"
        
        # Отримати лабель формату
        format_label = await self.repo.get_onix_label(150, product.product_form)
        
        # Отримати тип продукту
        product_type = map_form_to_type(product.product_form)
        
        # Отримати статус
        status = map_status(product.publishing_status)
        
        return ProductCardDTO(
            id=product.id,
            isbn=product.isbn_13,
            title=title,
            format=product.product_form,
            format_label=format_label,
            type=product_type,
            is_buyable=status.is_buyable,
            is_archived=status.is_archived,
        )
    
    async def _to_product_detail(self, product) -> ProductDetailDTO:
        """Маппінг ORM → ProductDetailDTO (з усіма деталями)."""
        # Базові
        title_obj = product.titles[0] if product.titles else None
        title_dto = TitleDTO(
            title=title_obj.title_text if title_obj else "—",
            subtitle=title_obj.subtitle if title_obj else None,
        )
        
        # Описання
        description = product.text_contents[0].text if product.text_contents else None
        
        # Формат
        format_label = await self.repo.get_onix_label(150, product.product_form)
        product_type = map_form_to_type(product.product_form)
        
        # Статус
        status_label = await self.repo.get_onix_label(64, product.publishing_status)
        status = map_status(product.publishing_status)
        
        # Мови
        languages = [lang.code for lang in product.languages]
        
        # Теми (THEMA)
        subjects = [
            SubjectDTO(
                code=subj.subject_code or "—",
                label=subj.subject_heading_text,
            )
            for subj in product.subjects
        ]
        
        # Автори
        contributors = []
        for link in product.contributors:
            role_label = await self.repo.get_onix_label(17, link.role)
            contributors.append(
                ContributorDTO(
                    name=link.contributor.name,
                    role=link.role,
                    role_label=role_label,
                )
            )
        
        # Розміри
        pages = product.extents[0].value if product.extents else None
        height_mm = None
        width_mm = None
        weight_g = None
        for measure in product.measures:
            if measure.type == "01":  # Height
                height_mm = int(measure.measurement)
            elif measure.type == "02":  # Width
                width_mm = int(measure.measurement)
            elif measure.type == "08":  # Weight
                weight_g = int(measure.measurement)
        
        # Видавець
        publisher = product.publisher.name if product.publisher else None
        
        # Дата публікації
        pub_date = product.publishing_dates[0] if product.publishing_dates else None
        published_at = pub_date.date_value if pub_date else None
        
        return ProductDetailDTO(
            id=product.id,
            isbn=product.isbn_13,
            ean=product.ean,
            sku=product.sku,
            title=title_dto,
            description=description,
            format=product.product_form,
            format_label=format_label,
            type=product_type,
            status=product.publishing_status,
            status_label=status_label,
            is_buyable=status.is_buyable,
            is_archived=status.is_archived,
            languages=languages,
            subjects=subjects,
            contributors=contributors,
            pages=int(pages) if pages else None,
            height_mm=height_mm,
            width_mm=width_mm,
            weight_g=weight_g,
            publisher=publisher,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
