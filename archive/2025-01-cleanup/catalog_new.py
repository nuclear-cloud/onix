"""
Models for new schema (async SQLAlchemy 2.x)
Compatible with Prisma schema definition
"""

from sqlalchemy import (
    BigInteger, Integer, String, Boolean, DateTime, Date, Numeric,
    Text, JSON, ARRAY, ForeignKey, UniqueConstraint, CheckConstraint,
    Index, text, Enum as SQLEnum
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)
from datetime import datetime
from typing import Optional, List
import uuid
import enum


class Base(AsyncAttrs, DeclarativeBase):
    pass


# ================================================================
# ENUMS
# ================================================================

class ContributorTypeEnum(str, enum.Enum):
    PERSON = "P"
    CORPORATE = "C"


class PublishingStatusEnum(str, enum.Enum):
    UNSPECIFIED = "00"
    ACTIVE = "01"
    OUT_OF_PRINT = "02"
    REPRINT = "03"
    NOT_YET_PUBLISHED = "04"
    CANCELLED = "05"
    RECALLED = "06"
    SUPERSEDED = "07"
    WITHDRAWN = "08"
    ACTIVE_NEW_EDITION = "09"


class OperationTypeEnum(str, enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


# ================================================================
# CATALOG PRODUCTS
# ================================================================

class CatalogProduct(Base):
    __tablename__ = "catalog_products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    
    # Identifiers
    isbn13: Mapped[Optional[str]] = mapped_column(String(13), unique=True)
    isbn10: Mapped[Optional[str]] = mapped_column(String(10))
    gtin14: Mapped[Optional[str]] = mapped_column(String(14))
    proprietary_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Titles
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    subtitle: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Collection
    collection_title: Mapped[Optional[str]] = mapped_column(String(300))
    collection_issn: Mapped[Optional[str]] = mapped_column(String(20))
    part_number: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Product form
    product_form_code: Mapped[str] = mapped_column(String(2), nullable=False)
    product_form_detail_code: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Physical properties
    page_count: Mapped[Optional[int]]
    width_mm: Mapped[Optional[Numeric]]
    height_mm: Mapped[Optional[Numeric]]
    thickness_mm: Mapped[Optional[Numeric]]
    weight_g: Mapped[Optional[Numeric]]
    
    # Language & region
    language_code: Mapped[str] = mapped_column(String(3), default="ukr")
    
    # Publisher
    publisher_name: Mapped[Optional[str]] = mapped_column(String(300))
    publisher_id: Mapped[Optional[str]] = mapped_column(String(50))
    imprint_name: Mapped[Optional[str]] = mapped_column(String(300))
    
    # Publishing
    publishing_status_code: Mapped[str] = mapped_column(String(2), nullable=False)
    publication_date: Mapped[Optional[Date]]
    out_of_print_date: Mapped[Optional[Date]]
    
    # Audience
    audience_code: Mapped[Optional[str]] = mapped_column(String(2))
    audience_range_qualifier: Mapped[Optional[str]] = mapped_column(String(10))
    audience_range_from: Mapped[Optional[int]]
    audience_range_to: Mapped[Optional[int]]
    
    # Classification
    primary_subject_scheme: Mapped[Optional[str]] = mapped_column(String(10))
    primary_subject_code: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Ukrainian codes
    udc_code: Mapped[Optional[str]] = mapped_column(String(50))
    bbk_code: Mapped[Optional[str]] = mapped_column(String(50))
    dk_018_code: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Semantic search
    embedding: Mapped[Optional[str]] = mapped_column(String)  # vector type stored as string
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relations
    contributors: Mapped[List["Contributor"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    subjects: Mapped[List["Subject"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    text_content: Mapped[List["TextContent"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    media_files: Mapped[List["MediaFile"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    prices: Mapped[List["Price"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    sales_rights: Mapped[List["SalesRight"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    related_products_from: Mapped[List["RelatedProduct"]] = relationship(
        "RelatedProduct",
        foreign_keys="RelatedProduct.product_id",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    related_products_to: Mapped[List["RelatedProduct"]] = relationship(
        "RelatedProduct",
        foreign_keys="RelatedProduct.related_product_id",
        back_populates="related_product",
    )
    
    __table_args__ = (
        Index("idx_products_isbn13", isbn13),
        Index("idx_products_status", publishing_status_code),
        Index("idx_products_publisher", publisher_name),
        Index("idx_products_form", product_form_code),
        Index("idx_products_language", language_code),
        Index("idx_products_publication_date", publication_date),
        Index("idx_products_metadata", metadata, postgresql_using="gin"),
        Index("idx_products_deleted", deleted_at),
        CheckConstraint(
            "isbn13 ~ '^[0-9]{13}$' OR isbn13 IS NULL",
            name="chk_isbn13"
        ),
    )


# ================================================================
# CONTRIBUTORS
# ================================================================

class Contributor(Base):
    __tablename__ = "contributors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_products.id", ondelete="CASCADE")
    )
    
    # Role
    role_code: Mapped[str] = mapped_column(String(3), nullable=False)
    sequence_number: Mapped[Optional[int]]
    
    # Type & name
    contributor_type: Mapped[str] = mapped_column(String(1), nullable=False)
    person_name: Mapped[Optional[str]] = mapped_column(String(300))
    person_name_inverted: Mapped[Optional[str]] = mapped_column(String(300))
    key_names: Mapped[Optional[str]] = mapped_column(String(200))
    names_before_key: Mapped[Optional[str]] = mapped_column(String(200))
    corporate_name: Mapped[Optional[str]] = mapped_column(String(300))
    
    # Bio
    biographical_note: Mapped[Optional[str]]
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    # Relations
    product: Mapped["CatalogProduct"] = relationship(back_populates="contributors")
    
    __table_args__ = (
        Index("idx_contributors_product", product_id),
        Index("idx_contributors_role", role_code),
        Index("idx_contributors_name", person_name),
        CheckConstraint(
            "(contributor_type = 'P' AND person_name IS NOT NULL) OR "
            "(contributor_type = 'C' AND corporate_name IS NOT NULL)",
            name="chk_contributor_name"
        ),
    )


# ================================================================
# SUBJECTS
# ================================================================

class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_products.id", ondelete="CASCADE")
    )
    
    scheme_code: Mapped[str] = mapped_column(String(10), nullable=False)
    subject_code: Mapped[Optional[str]] = mapped_column(String(100))
    subject_heading_text: Mapped[str] = mapped_column(String(500), nullable=False)
    
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    sequence_number: Mapped[Optional[int]]
    
    product: Mapped["CatalogProduct"] = relationship(back_populates="subjects")
    
    __table_args__ = (
        Index("idx_subjects_product", product_id),
        Index("idx_subjects_scheme", scheme_code),
        Index("idx_subjects_code", subject_code),
        Index("idx_subjects_primary", product_id, is_primary),
    )


# ================================================================
# TEXT CONTENT
# ================================================================

class TextContent(Base):
    __tablename__ = "text_content"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_products.id", ondelete="CASCADE")
    )
    
    text_type_code: Mapped[str] = mapped_column(String(2), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(200))
    source_title: Mapped[Optional[str]] = mapped_column(String(300))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    product: Mapped["CatalogProduct"] = relationship(back_populates="text_content")
    
    __table_args__ = (
        Index("idx_text_content_product", product_id),
        Index("idx_text_content_type", text_type_code),
    )


# ================================================================
# MEDIA FILES
# ================================================================

class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_products.id", ondelete="CASCADE")
    )
    
    resource_content_type_code: Mapped[str] = mapped_column(String(2), nullable=False)
    resource_mode_code: Mapped[str] = mapped_column(String(2), nullable=False)
    
    file_format_code: Mapped[Optional[str]] = mapped_column(String(2))
    file_link_type: Mapped[Optional[str]] = mapped_column(String(2))
    file_link: Mapped[str] = mapped_column(String, nullable=False)
    
    width_px: Mapped[Optional[int]]
    height_px: Mapped[Optional[int]]
    file_size_bytes: Mapped[Optional[int]]
    
    sequence_number: Mapped[Optional[int]]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    product: Mapped["CatalogProduct"] = relationship(back_populates="media_files")
    
    __table_args__ = (
        Index("idx_media_product", product_id),
        Index("idx_media_type", resource_content_type_code),
    )


# ================================================================
# PRICE SOURCE
# ================================================================

class PriceSource(Base):
    __tablename__ = "price_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    api_endpoint: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    prices: Mapped[List["Price"]] = relationship(back_populates="source")
    
    __table_args__ = (
        Index("idx_price_sources_active", is_active),
    )


# ================================================================
# PRICES
# ================================================================

class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_products.id", ondelete="CASCADE")
    )
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("price_sources.id")
    )
    
    price_type_code: Mapped[str] = mapped_column(String(2), nullable=False)
    price_amount: Mapped[Numeric] = mapped_column(Numeric(12, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), default="UAH")
    
    tax_type_code: Mapped[Optional[str]] = mapped_column(String(2))
    tax_rate_percent: Mapped[Optional[Numeric]] = mapped_column(Numeric(5, 2))
    tax_amount: Mapped[Optional[Numeric]] = mapped_column(Numeric(12, 2))
    
    price_effective_from: Mapped[Optional[Date]]
    price_effective_until: Mapped[Optional[Date]]
    
    discount_percent: Mapped[Optional[Numeric]] = mapped_column(Numeric(5, 2))
    stock_quantity: Mapped[Optional[int]]
    
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    product: Mapped["CatalogProduct"] = relationship(back_populates="prices")
    source: Mapped["PriceSource"] = relationship(back_populates="prices")
    
    __table_args__ = (
        Index("idx_prices_product", product_id, recorded_at.desc()),
        Index("idx_prices_source", source_id, recorded_at.desc()),
        Index("idx_prices_current", product_id, source_id, recorded_at.desc()),
    )


# ================================================================
# SALES RIGHTS
# ================================================================

class SalesRight(Base):
    __tablename__ = "sales_rights"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_products.id", ondelete="CASCADE")
    )
    
    sales_rights_type_code: Mapped[str] = mapped_column(String(2), nullable=False)
    territory_countries: Mapped[Optional[list]] = mapped_column(ARRAY(String(10)))
    territory_regions: Mapped[Optional[list]] = mapped_column(ARRAY(String(10)))
    
    start_date: Mapped[Optional[Date]]
    end_date: Mapped[Optional[Date]]
    
    product: Mapped["CatalogProduct"] = relationship(back_populates="sales_rights")
    
    __table_args__ = (
        Index("idx_sales_rights_product", product_id),
        Index("idx_sales_rights_countries", territory_countries, postgresql_using="gin"),
    )


# ================================================================
# RELATED PRODUCTS
# ================================================================

class RelatedProduct(Base):
    __tablename__ = "related_products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_products.id", ondelete="CASCADE")
    )
    related_product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_products.id", ondelete="CASCADE")
    )
    
    relation_code: Mapped[str] = mapped_column(String(2), nullable=False)
    
    product: Mapped["CatalogProduct"] = relationship(
        "CatalogProduct",
        foreign_keys=[product_id],
        back_populates="related_products_from"
    )
    related_product: Mapped["CatalogProduct"] = relationship(
        "CatalogProduct",
        foreign_keys=[related_product_id],
        back_populates="related_products_to"
    )
    
    __table_args__ = (
        UniqueConstraint("product_id", "related_product_id", name="uq_product_relation"),
        Index("idx_related_from", product_id),
        Index("idx_related_to", related_product_id),
        CheckConstraint("product_id != related_product_id", name="chk_no_self_relation"),
    )


# ================================================================
# AUDIT LOG
# ================================================================

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    table_name: Mapped[str] = mapped_column(String(50), nullable=False)
    record_id: Mapped[int] = mapped_column(BigInteger)
    operation: Mapped[str] = mapped_column(String(10), nullable=False)
    old_data: Mapped[Optional[dict]] = mapped_column(JSON)
    new_data: Mapped[Optional[dict]] = mapped_column(JSON)
    changed_by: Mapped[Optional[str]] = mapped_column(String(100))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    
    __table_args__ = (
        Index("idx_audit_table_record", table_name, record_id),
        Index("idx_audit_time", changed_at),
    )


# ================================================================
# CODE LISTS
# ================================================================

class CodeListProductForm(Base):
    __tablename__ = "code_list_product_form"
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50))


class CodeListPublishingStatus(Base):
    __tablename__ = "code_list_publishing_status"
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)


class CodeListContributorRole(Base):
    __tablename__ = "code_list_contributor_role"
    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50))


class CodeListPriceType(Base):
    __tablename__ = "code_list_price_type"
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)


class CodeListTextType(Base):
    __tablename__ = "code_list_text_type"
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)


class CodeListAudience(Base):
    __tablename__ = "code_list_audience"
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)


class CodeListSubjectScheme(Base):
    __tablename__ = "code_list_subject_scheme"
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500))
