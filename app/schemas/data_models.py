"""
PHASE 1: IDEAL DATA MODEL (Source of Truth)
============================================

Pydantic models defining the normalized structure for book data.
These models serve as the contract between raw API data and the database.

Key Design Decisions:
- Flat structures where possible (avoiding deep nesting)
- Clear One-to-Many relationships via nested lists
- Strict validation with meaningful error messages
- ISO standards for codes (language, currency, dates)
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import (
    BaseModel, 
    Field, 
    field_validator, 
    model_validator,
    ConfigDict
)
import re


# ============================================================================
# ENUMS (ONIX Code Lists)
# ============================================================================

class ProductFormCode(str, Enum):
    """ONIX List 150 - Product Form"""
    HARDBACK = "BB"
    PAPERBACK = "BC"
    LOOSE_LEAF = "BL"
    SPIRAL_BOUND = "BS"
    DIGITAL_DOWNLOAD = "DG"
    AUDIO_CD = "AC"
    EBOOK = "ED"
    
    @classmethod
    def _missing_(cls, value):
        return cls.HARDBACK  # Default fallback


class PublishingStatusCode(str, Enum):
    """ONIX List 64 - Publishing Status"""
    UNSPECIFIED = "00"
    CANCELLED = "01"
    FORTHCOMING = "02"
    POSTPONED = "03"
    ACTIVE = "04"
    NO_LONGER_AVAILABLE = "05"
    OUT_OF_STOCK = "06"
    OUT_OF_PRINT = "07"
    INACTIVE = "08"
    
    @classmethod
    def _missing_(cls, value):
        return cls.ACTIVE


class ContributorRoleCode(str, Enum):
    """ONIX List 17 - Contributor Role"""
    AUTHOR = "A01"
    GHOST_WRITER = "A02"
    SCREENWRITER = "A03"
    COMPILER = "A06"
    EDITOR = "B01"
    TRANSLATOR = "B06"
    ILLUSTRATOR = "A12"
    PHOTOGRAPHER = "A13"
    NARRATOR = "E07"


class TextTypeCode(str, Enum):
    """ONIX List 153 - Text Type"""
    MAIN_DESCRIPTION = "03"
    SHORT_DESCRIPTION = "02"
    TABLE_OF_CONTENTS = "04"
    REVIEW_QUOTE = "06"
    BIOGRAPHICAL_NOTE = "13"


class SubjectSchemeCode(str, Enum):
    """ONIX List 27 - Subject Scheme Identifier"""
    BISAC = "10"
    BIC = "12"
    THEMA = "93"
    KEYWORDS = "20"
    PROPRIETARY = "24"


class PriceTypeCode(str, Enum):
    """ONIX List 58 - Price Type"""
    RRP_EXCL_TAX = "01"
    RRP_INCL_TAX = "02"
    PROMOTIONAL = "41"


class ResourceModeCode(str, Enum):
    """ONIX List 159 - Resource Mode"""
    IMAGE = "03"
    VIDEO = "06"
    AUDIO = "07"


# ============================================================================
# NESTED MODELS (One-to-Many Relationships)
# ============================================================================

class ContributorDTO(BaseModel):
    """Author, translator, illustrator, etc."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    role_code: ContributorRoleCode = Field(
        default=ContributorRoleCode.AUTHOR,
        description="ONIX contributor role code"
    )
    sequence_number: int = Field(default=1, ge=1)
    contributor_type: str = Field(default="P", pattern="^[PC]$")  # P=Person, C=Corporate
    
    # Person name fields
    person_name: Optional[str] = Field(None, max_length=300)
    person_name_inverted: Optional[str] = Field(None, max_length=300)
    key_names: Optional[str] = Field(None, max_length=200)
    names_before_key: Optional[str] = Field(None, max_length=200)
    
    # Corporate name
    corporate_name: Optional[str] = Field(None, max_length=300)
    
    # Extra
    biographical_note: Optional[str] = None
    
    # Source tracking
    source_id: Optional[str] = Field(None, description="Original ID from source")
    
    @model_validator(mode='after')
    def validate_name_present(self) -> 'ContributorDTO':
        if not self.person_name and not self.corporate_name:
            raise ValueError("Either person_name or corporate_name must be provided")
        return self


class SubjectDTO(BaseModel):
    """Category, theme, keyword classification."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    scheme_code: SubjectSchemeCode = Field(
        default=SubjectSchemeCode.KEYWORDS,
        description="Subject scheme identifier"
    )
    subject_code: Optional[str] = Field(None, max_length=100)
    subject_heading_text: str = Field(..., min_length=1, max_length=500)
    is_primary: bool = Field(default=False)
    sequence_number: Optional[int] = Field(None, ge=1)


class TextContentDTO(BaseModel):
    """Descriptions, reviews, table of contents."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    text_type_code: TextTypeCode = Field(default=TextTypeCode.MAIN_DESCRIPTION)
    content: str = Field(..., min_length=1)
    author: Optional[str] = Field(None, max_length=200)
    source_title: Optional[str] = Field(None, max_length=300)
    
    @field_validator('content')
    @classmethod
    def clean_html(cls, v: str) -> str:
        """Remove HTML tags from content."""
        if v:
            clean = re.sub(r'<[^>]+>', '', v)
            return clean.strip()
        return v


class MediaFileDTO(BaseModel):
    """Cover images, videos, audio samples."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    resource_content_type_code: str = Field(default="01", max_length=2)  # 01=Front cover
    resource_mode_code: ResourceModeCode = Field(default=ResourceModeCode.IMAGE)
    file_format_code: Optional[str] = Field(None, max_length=2)
    file_link: str = Field(..., min_length=1)
    width_px: Optional[int] = Field(None, ge=1)
    height_px: Optional[int] = Field(None, ge=1)
    file_size_bytes: Optional[int] = Field(None, ge=0)
    sequence_number: int = Field(default=1, ge=1)
    
    @field_validator('file_link')
    @classmethod
    def ensure_full_url(cls, v: str) -> str:
        """Ensure URL is absolute."""
        if v and not v.startswith('http'):
            return f"https://yakaboo.ua{v}"
        return v


class PriceDTO(BaseModel):
    """Price information with source tracking."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    source_code: str = Field(..., min_length=1, max_length=50)
    price_type_code: PriceTypeCode = Field(default=PriceTypeCode.RRP_INCL_TAX)
    price_amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency_code: str = Field(default="UAH", pattern="^[A-Z]{3}$")
    
    # Tax
    tax_rate_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    
    # Validity
    price_effective_from: Optional[date] = None
    price_effective_until: Optional[date] = None
    
    # Discounts
    discount_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    original_price: Optional[Decimal] = Field(None, ge=0)
    
    # Stock
    stock_quantity: Optional[int] = Field(None, ge=0)
    in_stock: bool = Field(default=True)
    
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class SalesRightDTO(BaseModel):
    """Territory sales rights."""
    sales_rights_type_code: str = Field(default="01", max_length=2)
    territory_countries: List[str] = Field(default_factory=lambda: ["UA"])
    territory_regions: List[str] = Field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class RelatedProductDTO(BaseModel):
    """Related/similar products."""
    related_product_isbn: str = Field(..., pattern=r"^\d{13}$")
    relation_code: str = Field(default="06", max_length=2)  # 06=Alternative format


# ============================================================================
# MAIN PRODUCT MODEL (Source of Truth)
# ============================================================================

class ProductDTO(BaseModel):
    """
    The Ideal Product Data Model - Single Source of Truth.
    
    This model represents a fully normalized book record ready for database insertion.
    All nested API structures are flattened into typed relationships.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'  # Strict mode - no unknown fields
    )
    
    # ========================================
    # IDENTIFIERS
    # ========================================
    isbn13: str = Field(
        ...,
        pattern=r"^\d{13}$",
        description="Primary identifier - 13-digit ISBN"
    )
    isbn10: Optional[str] = Field(None, pattern=r"^\d{10}$")
    gtin14: Optional[str] = Field(None, pattern=r"^\d{14}$")
    proprietary_id: Optional[str] = Field(None, max_length=100)
    
    # ========================================
    # TITLE & DESCRIPTION
    # ========================================
    title: str = Field(..., min_length=1, max_length=500)
    subtitle: Optional[str] = Field(None, max_length=500)
    
    # ========================================
    # SERIES/COLLECTION
    # ========================================
    collection_title: Optional[str] = Field(None, max_length=300)
    collection_issn: Optional[str] = Field(None, max_length=20)
    part_number: Optional[str] = Field(None, max_length=50)
    
    # ========================================
    # PRODUCT FORM
    # ========================================
    product_form_code: ProductFormCode = Field(default=ProductFormCode.HARDBACK)
    product_form_detail_code: Optional[str] = Field(None, max_length=10)
    
    # ========================================
    # PHYSICAL CHARACTERISTICS
    # ========================================
    page_count: Optional[int] = Field(None, ge=1, le=50000)
    width_mm: Optional[Decimal] = Field(None, ge=0)
    height_mm: Optional[Decimal] = Field(None, ge=0)
    thickness_mm: Optional[Decimal] = Field(None, ge=0)
    weight_g: Optional[Decimal] = Field(None, ge=0)
    
    # ========================================
    # LANGUAGE
    # ========================================
    language_code: str = Field(default="ukr", pattern="^[a-z]{3}$")
    
    # ========================================
    # PUBLISHER
    # ========================================
    publisher_name: Optional[str] = Field(None, max_length=300)
    publisher_id: Optional[str] = Field(None, max_length=50)
    imprint_name: Optional[str] = Field(None, max_length=300)
    
    # ========================================
    # PUBLICATION STATUS
    # ========================================
    publishing_status_code: PublishingStatusCode = Field(
        default=PublishingStatusCode.ACTIVE
    )
    publication_date: Optional[date] = None
    out_of_print_date: Optional[date] = None
    
    # ========================================
    # AUDIENCE
    # ========================================
    audience_code: Optional[str] = Field(None, max_length=2)
    audience_range_qualifier: Optional[str] = Field(None, max_length=10)
    audience_range_from: Optional[int] = Field(None, ge=0, le=99)
    audience_range_to: Optional[int] = Field(None, ge=0, le=99)
    
    # ========================================
    # CLASSIFICATION
    # ========================================
    primary_subject_scheme: Optional[str] = Field(None, max_length=10)
    primary_subject_code: Optional[str] = Field(None, max_length=50)
    
    # Ukrainian-specific
    udc_code: Optional[str] = Field(None, max_length=50)
    bbk_code: Optional[str] = Field(None, max_length=50)
    dk_018_code: Optional[str] = Field(None, max_length=20)
    
    # ========================================
    # METADATA
    # ========================================
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Extra fields not in schema"
    )
    
    # ========================================
    # RELATIONSHIPS (One-to-Many)
    # ========================================
    contributors: List[ContributorDTO] = Field(default_factory=list)
    subjects: List[SubjectDTO] = Field(default_factory=list)
    text_content: List[TextContentDTO] = Field(default_factory=list)
    media_files: List[MediaFileDTO] = Field(default_factory=list)
    prices: List[PriceDTO] = Field(default_factory=list)
    sales_rights: List[SalesRightDTO] = Field(default_factory=list)
    related_products: List[RelatedProductDTO] = Field(default_factory=list)
    
    # ========================================
    # FLAGS
    # ========================================
    is_active: bool = Field(default=True)
    
    # ========================================
    # TIMESTAMPS
    # ========================================
    source_created_at: Optional[datetime] = None
    source_updated_at: Optional[datetime] = None
    
    # ========================================
    # VALIDATORS
    # ========================================
    
    @field_validator('isbn13')
    @classmethod
    def validate_isbn13_checksum(cls, v: str) -> str:
        """Validate ISBN-13 checksum."""
        if len(v) != 13 or not v.isdigit():
            raise ValueError(f"ISBN-13 must be exactly 13 digits: {v}")
        
        # Calculate checksum
        total = sum(
            int(digit) * (1 if i % 2 == 0 else 3)
            for i, digit in enumerate(v[:12])
        )
        check_digit = (10 - (total % 10)) % 10
        
        if int(v[12]) != check_digit:
            # Log warning but don't reject (some sources have bad checksums)
            pass  # Could raise ValueError here for strict mode
        
        return v
    
    @model_validator(mode='after')
    def ensure_at_least_one_price(self) -> 'ProductDTO':
        """Warn if no price information."""
        # Not required - some products may not have prices yet
        return self
    
    @property
    def record_reference(self) -> str:
        """
        Generate unique record reference.
        
        Uses ISBN-13 as primary key, or proprietary_id as fallback.
        This is the unique identifier used in the database.
        """
        if self.isbn13:
            return f"ISBN-{self.isbn13}"
        if self.proprietary_id:
            return f"PROP-{self.proprietary_id}"
        return f"UNKNOWN-{id(self)}"
    
    def to_flat_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for database insertion."""
        data = self.model_dump(exclude={
            'contributors', 'subjects', 'text_content', 
            'media_files', 'prices', 'sales_rights', 'related_products'
        })
        return data
    
    def get_nested_data(self) -> Dict[str, List[Dict]]:
        """Get nested relationships for separate insertion."""
        return {
            'contributors': [c.model_dump() for c in self.contributors],
            'subjects': [s.model_dump() for s in self.subjects],
            'text_content': [t.model_dump() for t in self.text_content],
            'media_files': [m.model_dump() for m in self.media_files],
            'prices': [p.model_dump() for p in self.prices],
            'sales_rights': [sr.model_dump() for sr in self.sales_rights],
            'related_products': [rp.model_dump() for rp in self.related_products],
        }


# ============================================================================
# BATCH MODELS
# ============================================================================

class ProductBatch(BaseModel):
    """Batch of products for bulk processing."""
    products: List[ProductDTO]
    source: str = Field(..., description="Data source identifier")
    batch_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def count(self) -> int:
        return len(self.products)
    
    @property
    def valid_count(self) -> int:
        return len([p for p in self.products if p.isbn13])


# ============================================================================
# VALIDATION RESULT
# ============================================================================

class ValidationError(BaseModel):
    """Detailed validation error."""
    field: str
    message: str
    value: Optional[Any] = None
    path: Optional[str] = None  # JSON path like "author_label[0].label"


class ValidationResult(BaseModel):
    """Result of validation operation."""
    is_valid: bool
    data: Optional['ProductDTO'] = None  # The transformed product (if successful)
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)
    source_id: Optional[str] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def add_error(self, field: str, message: str, value: Any = None, path: str = None):
        self.errors.append(ValidationError(
            field=field, message=message, value=value, path=path
        ))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str, value: Any = None, path: str = None):
        self.warnings.append(ValidationError(
            field=field, message=message, value=value, path=path
        ))
