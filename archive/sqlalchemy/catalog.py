"""
Catalog Models (ONIX-Coded) - FULL NORMALIZATION (V3.0 STRICT).

Goal: 100% Relational coverage of ONIX 3.0 example.
JSONB is ONLY for unknown/future fields.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, func, Boolean, Enum as SQLEnum, DECIMAL, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref, foreign

from app.core.database import Base
from app.models.codes_v71 import (
    ProductForm,
    ProductFormDetail,
    ContributorRole,
    PublishingStatus,
    NotificationType,
    TitleType,
    ExtentType,
    MeasureType,
    MeasureUnit,
    PriceType,
    SubjectSchemeIdentifier,
    TextContentType,
    ProductAvailability,
    CollectionType, # New
    CollectionSequenceType, # New
    DateType, # New: for PublishingDate
    ProductRelation, # New
    AudienceRangeQualifier, # New
    AudienceRangePrecision, # New
    LanguageRole, # New
    RegionCode, # New (for PrizeCountry)
)


class RefOnixCodelist(Base):
    """
    Reference table for ONIX codelists (Issue 71).
    Stores list number and code metadata for validation and lookups.
    """

    __tablename__ = "ref_onix_codelists"

    list_number = Column(Integer, primary_key=True)
    code = Column(String(50), primary_key=True)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    issue_number = Column(String(10), nullable=True)
    modified_number = Column(String(10), nullable=True)
    deprecated_number = Column(String(10), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)

    __table_args__ = (
        Index("ix_ref_onix_codelists_list_number", "list_number"),
    )

# --- Shared Entities ---

class Publisher(Base):
    """
    Publisher entity (Видавництво).
    """
    __tablename__ = "catalog_publishers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    gln = Column(String(13), nullable=True) 
    
    products = relationship("CatalogProduct", back_populates="publisher")


class Contributor(Base):
    """
    Normalized Author/Contributor Registry.
    """
    __tablename__ = "catalog_contributors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True) # "Stephen King"
    person_name_inverted = Column(String(255), nullable=True) # "King, Stephen"
    biographical_note = Column(Text, nullable=True)
    
    product_links = relationship("CatalogProductContributor", back_populates="contributor")


class Collection(Base):
    """
    Series / Collections (Серії книг).
    Normalized to allow reusing series across books.
    """
    __tablename__ = "catalog_collections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(1000), nullable=False, index=True) # "Українська класика в коміксах"
    type = Column(SQLEnum(CollectionType))
    issn = Column(String(8), nullable=True) # Series ISSN
    
    product_links = relationship("CatalogProductCollection", back_populates="collection")


# --- Main Product ---

class CatalogProduct(Base):
    """
    Central product registry <Product>.
    """
    __tablename__ = "catalog_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # --- Administrative ---
    record_reference = Column(String(100), unique=True, nullable=False, index=True) # 978-966...
    notification_type = Column(SQLEnum(NotificationType))
    
    # --- Identifiers ---
    isbn_13 = Column(String(13), unique=True, nullable=True, index=True)
    ean = Column(String(13), unique=True, nullable=True)
    sku = Column(String(50), nullable=True, index=True) # Proprietary ID
    
    # --- Descriptive (Flat main props) ---
    product_form = Column(SQLEnum(ProductForm), nullable=False, index=True)
    product_form_detail = Column(SQLEnum(ProductFormDetail), nullable=True)
    edition_number = Column(Integer, nullable=True)
    
    # --- Status ---
    publishing_status = Column(SQLEnum(PublishingStatus))
    is_ukrainian = Column(Boolean, default=True, index=True)
    
    # Fallback
    onix_full = Column(JSONB, nullable=True)
    
    # --- System ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # --- Relationships ---
    publisher_id = Column(UUID(as_uuid=True), ForeignKey("catalog_publishers.id"), nullable=True)
    publisher = relationship("Publisher", back_populates="products")
    
    # 1. Titles
    titles = relationship("CatalogTitle", back_populates="product", cascade="all, delete-orphan")
    
    # 2. Contributors
    contributors = relationship("CatalogProductContributor", back_populates="product", cascade="all, delete-orphan")
    
    # 3. Measures & Extents
    measures = relationship("CatalogMeasure", back_populates="product", cascade="all, delete-orphan")
    extents = relationship("CatalogExtent", back_populates="product", cascade="all, delete-orphan")
    
    # 4. Subjects (Topics)
    subjects = relationship("CatalogSubject", back_populates="product", cascade="all, delete-orphan")
    
    # 5. Audience
    audience_ranges = relationship("CatalogAudienceRange", back_populates="product", cascade="all, delete-orphan")
    
    # 6. Languages
    languages = relationship("CatalogLanguage", back_populates="product", cascade="all, delete-orphan")
    
    # 7. Collections (Series)
    collections = relationship("CatalogProductCollection", back_populates="product", cascade="all, delete-orphan")
    
    # 8. Prizes
    prizes = relationship("CatalogPrize", back_populates="product", cascade="all, delete-orphan")
    
    # 9. Text Content (Reviews, Descriptions)
    text_contents = relationship("CatalogTextContent", back_populates="product", cascade="all, delete-orphan")
    cited_contents = relationship("CatalogCitedContent", back_populates="product", cascade="all, delete-orphan")
    
    # 10. Related Products
    related_products = relationship("CatalogRelatedProduct", back_populates="product", cascade="all, delete-orphan")
    
    # 11. Publishing Dates
    publishing_dates = relationship("CatalogPublishingDate", back_populates="product", cascade="all, delete-orphan")


# --- Junction Tables ---

class CatalogProductContributor(Base):
    """
    Product <-> Author Link.
    Includes SequenceNumber.
    """
    __tablename__ = "catalog_product_contributors_link"

    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), primary_key=True)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("catalog_contributors.id", ondelete="CASCADE"), primary_key=True)
    
    role = Column(SQLEnum(ContributorRole), nullable=False, primary_key=True)
    sequence_number = Column(Integer, default=1)
    
    product = relationship("CatalogProduct", back_populates="contributors")
    contributor = relationship("Contributor", back_populates="product_links")

class CatalogProductCollection(Base):
    """
    Product <-> Series Link.
    Includes Number in Series.
    """
    __tablename__ = "catalog_product_collections_link"
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), primary_key=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("catalog_collections.id", ondelete="CASCADE"), primary_key=True)
    
    sequence_type = Column(SQLEnum(CollectionSequenceType))
    sequence_number = Column(String(50), nullable=True) # "5", "Vol. 2"
    
    product = relationship("CatalogProduct", back_populates="collections")
    collection = relationship("Collection", back_populates="product_links")


# --- Detail Tables ---

class CatalogTitle(Base):
    """
    <TitleDetail>
    """
    __tablename__ = "catalog_titles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    type = Column(SQLEnum(TitleType), nullable=False)
    
    # Flattened TitleElement
    title_text = Column(Text, nullable=False)
    subtitle = Column(Text, nullable=True)
    
    product = relationship("CatalogProduct", back_populates="titles")

class CatalogLanguage(Base):
    """
    <Language>
    """
    __tablename__ = "catalog_languages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(SQLEnum(LanguageRole))
    code = Column(String(3), nullable=False) # ISO 639-2 (ukr, eng)
    
    product = relationship("CatalogProduct", back_populates="languages")

class CatalogExtent(Base):
    """
    <Extent>: Page count, Duration
    """
    __tablename__ = "catalog_extents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    type = Column(SQLEnum(ExtentType), nullable=False) # 00 = Main Content
    value = Column(DECIMAL(10, 2), nullable=False)
    unit = Column(String(10), nullable=True) # Pages, Hours
    
    product = relationship("CatalogProduct", back_populates="extents")

class CatalogMeasure(Base):
    """
    <Measure>: Height, Width, Weight
    """
    __tablename__ = "catalog_measures"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    type = Column(SQLEnum(MeasureType), nullable=False) # 01=Height, 02=Width
    measurement = Column(DECIMAL(10, 2), nullable=False)
    unit_code = Column(SQLEnum(MeasureUnit), nullable=False) # mm, gr
    
    product = relationship("CatalogProduct", back_populates="measures")

class RefThemaSubject(Base):
    """
    Reference table for Thema Classification.
    Stores codes and localized labels.
    """
    __tablename__ = "ref_thema_subjects"
    
    code = Column(String(20), primary_key=True) # e.g. "1DDB-BE-B"
    parent_code = Column(String(20), ForeignKey("ref_thema_subjects.code"), nullable=True)
    
    label_en = Column(String(255), nullable=False)
    label_uk = Column(String(255), nullable=True) # Ukrainian translation
    
    description_en = Column(Text, nullable=True)
    description_uk = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true", default=True)
    
    # Hierarchy
    children = relationship("RefThemaSubject", backref=backref("parent", remote_side=[code]))

    __table_args__ = (
        Index("ix_ref_thema_label_uk", "label_uk"),
    )


class CatalogSubject(Base):
    """
    <Subject>: Thema, BISAC, Keywords
    """
    __tablename__ = "catalog_subjects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    scheme_identifier = Column(SQLEnum(SubjectSchemeIdentifier), nullable=False)
    subject_code = Column(String(100), nullable=True)
    subject_heading_text = Column(String(500), nullable=True)
    
    # Link to Thema Reference (optional, only if scheme is Thema)
    thema_ref = relationship(
        "RefThemaSubject",
        primaryjoin="and_(foreign(CatalogSubject.subject_code) == RefThemaSubject.code, CatalogSubject.scheme_identifier == '93')",
        uselist=False,
        viewonly=True
    )
    
    product = relationship("CatalogProduct", back_populates="subjects")

class CatalogAudienceRange(Base):
    """
    <AudienceRange>: Age 16-99
    """
    __tablename__ = "catalog_audience_ranges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    qualifier = Column(SQLEnum(AudienceRangeQualifier))
    precision = Column(SQLEnum(AudienceRangePrecision))
    value = Column(String(10), nullable=False) # "16"
    
    product = relationship("CatalogProduct", back_populates="audience_ranges")

class CatalogPrize(Base):
    """
    <Prize>: Awards
    """
    __tablename__ = "catalog_prizes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False) # "BBC Book of the Year"
    year = Column(String(4), nullable=True)
    country = Column(SQLEnum(RegionCode), nullable=True) # UA
    code = Column(String(2), nullable=True) # 02 = Winner
    
    product = relationship("CatalogProduct", back_populates="prizes")

class CatalogTextContent(Base):
    """
    <TextContent>: Blurbs, Descriptions
    """
    __tablename__ = "catalog_text_contents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    type = Column(SQLEnum(TextContentType), nullable=False)
    text = Column(Text, nullable=False)
    author = Column(String(255), nullable=True)
    
    product = relationship("CatalogProduct", back_populates="text_contents")

class CatalogCitedContent(Base):
    """
    <CitedContent>: Reviews, Third-party quotes
    """
    __tablename__ = "catalog_cited_contents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    type = Column(String(2), nullable=False) # 06=Review Quote
    source_title = Column(String(255), nullable=True) # "NY Times"
    citation_note = Column(Text, nullable=True)
    link = Column(String(500), nullable=True) # URL
    
    product = relationship("CatalogProduct", back_populates="cited_contents")

class CatalogRelatedProduct(Base):
    """
    <RelatedProduct>: E-book version, etc.
    """
    __tablename__ = "catalog_related_products"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    relation_code = Column(SQLEnum(ProductRelation), nullable=False)
    related_product_id_type = Column(String(2), default="15") # ISBN
    related_product_id_value = Column(String(255), nullable=False)
    
    product = relationship("CatalogProduct", back_populates="related_products")

class CatalogPublishingDate(Base):
    """
    <PublishingDate>: Publication dates
    """
    __tablename__ = "catalog_publishing_dates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(SQLEnum(DateType), nullable=False) # 01=Publication Date
    date_value = Column(String(8), nullable=False) # YYYYMMDD
    date_format = Column(String(2), default="00")
    
    product = relationship("CatalogProduct", back_populates="publishing_dates")