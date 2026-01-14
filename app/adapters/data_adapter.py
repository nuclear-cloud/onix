"""
PHASE 2: ADAPTER INTERFACE & IMPLEMENTATION
============================================

Generic adapter interface and Yakaboo-specific implementation.

Design Pattern: Adapter + Strategy
- BaseAdapter defines the contract
- Each source (Yakaboo, KSD, Vivat) implements the interface
- Adapters handle recursive traversal, null safety, type casting
"""

from __future__ import annotations

import re
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional, Callable, TypeVar, Sequence
from dataclasses import dataclass, field

from app.schemas.data_models import (
    ProductDTO,
    ContributorDTO,
    SubjectDTO,
    TextContentDTO,
    MediaFileDTO,
    PriceDTO,
    SalesRightDTO,
    ProductFormCode,
    PublishingStatusCode,
    ContributorRoleCode,
    TextTypeCode,
    SubjectSchemeCode,
    PriceTypeCode,
    ResourceModeCode,
    ValidationResult,
    ValidationError,
)


logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# MAPPING ERROR TRACKING
# ============================================================================


@dataclass
class MappingContext:
    """Tracks current position in nested JSON for error reporting."""

    source_id: Optional[str] = None
    path: List[str] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)

    def push(self, key: str) -> "MappingContext":
        """Enter a nested level."""
        self.path.append(key)
        return self

    def pop(self) -> "MappingContext":
        """Exit a nested level."""
        if self.path:
            self.path.pop()
        return self

    @property
    def current_path(self) -> str:
        return ".".join(self.path) or "root"

    def add_error(self, field: str, message: str, value: Any = None):
        self.errors.append(
            {
                "path": f"{self.current_path}.{field}",
                "field": field,
                "message": message,
                "value": str(value)[:100] if value else None,
            }
        )

    def add_warning(self, field: str, message: str, value: Any = None):
        self.warnings.append(
            {
                "path": f"{self.current_path}.{field}",
                "field": field,
                "message": message,
                "value": str(value)[:100] if value else None,
            }
        )


# ============================================================================
# ADAPTER INTERFACE
# ============================================================================


class BaseDataAdapter(ABC):
    """
    Abstract base class for all data source adapters.

    Responsibilities:
    1. transform() - Convert raw JSON to ProductDTO
    2. validate() - Check data integrity before DB operations
    3. safe data extraction with default values
    """

    def __init__(self, source_name: str, source_code: str):
        self.source_name = source_name
        self.source_code = source_code
        self.stats = {"processed": 0, "successful": 0, "failed": 0, "warnings": 0}

    @abstractmethod
    def transform(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """
        Transform raw API JSON into ProductDTO.

        Args:
            raw_data: Raw JSON from the API

        Returns:
            ValidationResult with data, errors, and warnings
        """
        pass

    @abstractmethod
    def validate(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate raw data before transformation.

        Args:
            raw_data: Raw JSON from the API

        Returns:
            ValidationResult with is_valid flag and error details
        """
        pass

    @abstractmethod
    def extract_identifier(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """
        Quick extraction of primary identifier without full transform.

        Args:
            raw_data: Raw JSON from the API

        Returns:
            ISBN-13 or other primary identifier
        """
        pass

    def should_ingest(self, raw_data: Dict[str, Any]) -> bool:
        """Gatekeeper: decide if this record should ever hit the DB.

        This is meant to be fast and conservative: it runs before we write
        anything into `cold.RawIngestion`.

        Returns:
            (True, None) by default. Specific adapters may override.

        Notes:
            Use `should_ingest_with_reason` if you want to track skip reasons.
        """
        return True

    def should_ingest_with_reason(
        self, raw_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Gatekeeper with optional reason string.

        Default behavior delegates to `should_ingest`.
        """
        allowed = self.should_ingest(raw_data)
        return allowed, None if allowed else "filtered"

    # ========================================
    # SAFE VALUE EXTRACTION UTILITIES
    # ========================================

    @staticmethod
    def safe_str(
        value: Any, default: Optional[str] = None, max_length: Optional[int] = None
    ) -> Optional[str]:
        """Safely extract string value."""
        if value is None:
            return default
        result = str(value).strip()
        if not result:
            return default
        if max_length and len(result) > max_length:
            result = result[:max_length]
        return result

    @staticmethod
    def safe_int(
        value: Any,
        default: Optional[int] = None,
        min_val: Optional[int] = None,
        max_val: Optional[int] = None,
    ) -> Optional[int]:
        """Safely extract integer value with bounds checking."""
        if value is None:
            return default
        try:
            result = int(value)
            if min_val is not None and result < min_val:
                return default
            if max_val is not None and result > max_val:
                return default
            return result
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Safely extract float value."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_decimal(
        value: Any, default: Optional[Decimal] = None
    ) -> Optional[Decimal]:
        """Safely extract Decimal value."""
        if value is None:
            return default
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return default

    @staticmethod
    def safe_bool(value: Any, default: bool = False) -> bool:
        """Safely extract boolean value."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return default

    @staticmethod
    def safe_date(value: Any, formats: Optional[List[str]] = None) -> Optional[date]:
        """Safely parse date from various formats."""
        if value is None:
            return None

        formats = formats or [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%Y",
        ]

        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()

        value_str = str(value).strip()
        if not value_str:
            return None

        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue

        # Try year-only
        if value_str.isdigit() and len(value_str) == 4:
            try:
                year = int(value_str)
                if 1800 <= year <= 2100:
                    return date(year, 1, 1)
            except ValueError:
                pass

        return None

    @staticmethod
    def safe_datetime(value: Any) -> Optional[datetime]:
        """Safely parse datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
        ]

        value_str = str(value).strip()
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt)
            except ValueError:
                continue

        return None

    def safe_list(self, value: Any) -> List:
        """Safely extract list, handling None and non-list values."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def get_nested(self, data: Dict, *keys: str, default: Any = None) -> Any:
        """
        Safely navigate nested dictionary.

        Example:
            get_nested(data, 'author_label', '0', 'label')
            # Equivalent to data['author_label'][0]['label'] but safe
        """
        result = data
        for key in keys:
            if result is None:
                return default
            if isinstance(result, dict):
                result = result.get(key, default)
            elif isinstance(result, list):
                try:
                    idx = int(key)
                    result = result[idx] if 0 <= idx < len(result) else default
                except (ValueError, IndexError):
                    return default
            else:
                return default
        return result if result is not None else default

    def get_stats(self) -> Dict[str, int]:
        """Return processing statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {"processed": 0, "successful": 0, "failed": 0, "warnings": 0}


# ============================================================================
# YAKABOO ADAPTER IMPLEMENTATION
# ============================================================================


class YakabooDataAdapter(BaseDataAdapter):
    UKRAINIAN_LANGUAGE_ID = 332272
    BOOK_CATEGORY_ID = 4723
    BOOK_ATTRIBUTE_SET_IDS = {20, 211}  # 20=simple, 211=downloadable (e-books)

    def should_ingest(self, raw_data: Dict[str, Any]) -> bool:
        allowed, _ = self.should_ingest_with_reason(raw_data)
        return allowed

    def should_ingest_with_reason(
        self, raw_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        attribute_set_id = raw_data.get("attribute_set_id")
        if (
            attribute_set_id is not None
            and attribute_set_id not in self.BOOK_ATTRIBUTE_SET_IDS
        ):
            return False, "not_book"

        category_ids = raw_data.get("category_ids")
        if isinstance(category_ids, list) and self.BOOK_CATEGORY_ID not in category_ids:
            return False, "not_book"
        # If category_ids is None or not a list, skip the category check
        # (data might already be filtered or have different structure)

        language_code = self._map_language(raw_data)
        if language_code != "ukr":
            return False, "non_ukr"

        if not self.safe_str(raw_data.get("name")):
            return False, "missing_name"

        if not self.extract_identifier(raw_data):
            return False, "missing_isbn"

        return True, None

    """
    Concrete adapter for Yakaboo JSON format.

    Handles the complex nested structure with:
    - author_label[].label format
    - book_* prefixed fields
    - Multiple ID fields (sku, id, barcode, book_isbn)
    """

    # Language code mapping
    LANGUAGE_MAP = {
        332272: "ukr",  # Ukrainian
        332273: "rus",  # Russian
        332271: "eng",  # English (old)
        332987: "eng",  # English (main)
        332274: "pol",  # Polish
        332275: "deu",  # German
        332276: "fra",  # French
    }

    # Binding type to ONIX ProductForm mapping
    BINDING_MAP = {
        "тверд": ProductFormCode.HARDBACK,
        "hard": ProductFormCode.HARDBACK,
        "м'як": ProductFormCode.PAPERBACK,
        "мяг": ProductFormCode.PAPERBACK,
        "paper": ProductFormCode.PAPERBACK,
        "soft": ProductFormCode.PAPERBACK,
        "інтег": ProductFormCode.HARDBACK,  # Integral
    }

    def __init__(self):
        super().__init__(source_name="Yakaboo", source_code="yakaboo")

    def extract_identifier(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract ISBN-13 from Yakaboo data."""
        # Method 1: barcode field (often has ISBN)
        barcode = raw_data.get("barcode")
        if barcode:
            clean = str(barcode).replace("-", "").replace(" ", "")
            if len(clean) == 13 and clean.isdigit():
                return clean

        # Method 2: book_isbn field
        isbn = raw_data.get("book_isbn")
        if isbn:
            clean = str(isbn).replace("-", "").replace(" ", "")
            if len(clean) == 13 and clean.isdigit():
                return clean

        # Method 3: book_isbn_label array
        isbn_labels = raw_data.get("book_isbn_label", [])
        if isinstance(isbn_labels, list):
            for item in isbn_labels:
                if isinstance(item, dict):
                    label = item.get("label", "")
                    if label:
                        clean = str(label).replace("-", "").replace(" ", "")
                        if len(clean) == 13 and clean.isdigit():
                            return clean

        return None

    def validate(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """Validate Yakaboo data before transformation."""
        result = ValidationResult(
            is_valid=True,
            source_id=str(raw_data.get("id", raw_data.get("sku", "unknown"))),
        )

        # Check required fields
        isbn = self.extract_identifier(raw_data)
        if not isbn:
            result.add_error(
                "isbn13",
                "No valid ISBN-13 found in barcode, book_isbn, or book_isbn_label",
            )

        name = raw_data.get("name")
        if not name or not str(name).strip():
            result.add_error("title", "Product name is missing or empty")

        # Warnings for recommended fields
        if not raw_data.get("book_publisher_label"):
            result.add_warning("publisher", "No publisher information")

        if not raw_data.get("author_label"):
            result.add_warning("contributors", "No author information")

        return result

    def transform(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """Transform Yakaboo JSON to ProductDTO."""
        ctx = MappingContext(source_id=str(raw_data.get("id", "unknown")))
        self.stats["processed"] += 1

        result = ValidationResult(
            is_valid=True,
            source_id=str(raw_data.get("id", raw_data.get("sku", "unknown"))),
        )

        try:
            # Extract ISBN first (required)
            isbn13 = self.extract_identifier(raw_data)
            if not isbn13:
                result.add_error("isbn13", "No valid ISBN-13 found")
                result.is_valid = False
                self.stats["failed"] += 1
                return result

            # Build the ProductDTO
            product = ProductDTO(
                # Identifiers
                isbn13=isbn13,
                isbn10=None,
                gtin14=None,
                proprietary_id=self.safe_str(raw_data.get("sku")),
                # Title
                title=self.safe_str(
                    raw_data.get("name"), default="Без назви", max_length=500
                )
                or "Без назви",
                subtitle=self.safe_str(
                    raw_data.get("short_description"), max_length=500
                ),
                # Series/collection
                collection_title=None,
                collection_issn=None,
                part_number=None,
                # Product form
                product_form_code=self._map_product_form(raw_data),
                product_form_detail_code=None,
                # Physical
                page_count=self.safe_int(
                    raw_data.get("book_page_count"), min_val=1, max_val=50000
                ),
                width_mm=None,
                height_mm=None,
                thickness_mm=None,
                weight_g=None,
                # Language
                language_code=self._map_language(raw_data),
                # Publisher
                publisher_name=self._extract_label(raw_data, "book_publisher_label"),
                publisher_id=None,
                imprint_name=None,
                # Status
                publishing_status_code=self._map_status(raw_data),
                publication_date=self._extract_publication_date(raw_data),
                out_of_print_date=None,
                # Audience
                audience_code=None,
                audience_range_qualifier=None,
                audience_range_from=None,
                audience_range_to=None,
                # Classification
                primary_subject_scheme=None,
                primary_subject_code=None,
                udc_code=None,
                bbk_code=None,
                dk_018_code=None,
                # Relationships
                contributors=self._extract_contributors(raw_data, ctx),
                subjects=self._extract_subjects(raw_data, ctx),
                text_content=self._extract_text_content(raw_data, ctx),
                media_files=self._extract_media_files(raw_data, ctx),
                prices=self._extract_prices(raw_data, ctx),
                sales_rights=[SalesRightDTO(territory_countries=["UA"])],
                related_products=[],
                # Metadata - store extra fields
                metadata={
                    "source": {
                        "name": self.source_name,
                        "code": self.source_code,
                        "yakaboo": {
                            "id": raw_data.get("id"),
                            "sku": raw_data.get("sku"),
                            "url_key": raw_data.get("url_key"),
                            "attribute_set_id": raw_data.get("attribute_set_id"),
                        },
                    },
                    "catalog": {
                        "category_ids": raw_data.get("category_ids", []),
                    },
                    "metrics": {
                        "statistics_visits": raw_data.get("statistics_visits"),
                        "is_top_sale": raw_data.get("is_top_sale"),
                    },
                },
                # Flags
                is_active=raw_data.get("status") != "disabled",
                # Timestamps
                source_created_at=self.safe_datetime(raw_data.get("created_at")),
                source_updated_at=self.safe_datetime(raw_data.get("updated_at")),
            )

            result.data = product
            self.stats["successful"] += 1

            # Copy warnings from context
            for warning in ctx.warnings:
                result.add_warning(warning["field"], warning["message"])

            if ctx.warnings:
                self.stats["warnings"] += len(ctx.warnings)

            return result

        except Exception as e:
            result.add_error("transform", f"Transformation failed: {str(e)}")
            result.is_valid = False
            self.stats["failed"] += 1
            logger.exception(f"Transform error for {ctx.source_id}: {e}")
            return result

    # ========================================
    # PRIVATE MAPPING METHODS
    # ========================================

    def _extract_label(self, raw_data: Dict, field_name: str) -> Optional[str]:
        """Extract first label from Yakaboo label array."""
        labels = raw_data.get(field_name, [])
        if isinstance(labels, list) and labels:
            first = labels[0]
            if isinstance(first, dict):
                return self.safe_str(first.get("label"))
            return self.safe_str(first)
        return None

    def _map_product_form(self, raw_data: Dict) -> ProductFormCode:
        """Map Yakaboo binding to ONIX ProductForm."""
        binding = self._extract_label(raw_data, "book_binding_type_label")
        if binding:
            binding_lower = binding.lower()
            for key, form in self.BINDING_MAP.items():
                if key in binding_lower:
                    return form
        return ProductFormCode.HARDBACK

    def _map_language(self, raw_data: Dict) -> str:
        """Map Yakaboo language ID to ISO 639-2 code."""
        lang_ids = raw_data.get("book_lang", [])
        if isinstance(lang_ids, list) and lang_ids:
            lang_id = lang_ids[0]
            return self.LANGUAGE_MAP.get(lang_id, "ukr")
        return "ukr"

    def _map_status(self, raw_data: Dict) -> PublishingStatusCode:
        """Map Yakaboo status to ONIX PublishingStatus."""
        status = raw_data.get("status")
        if status == "disabled" or status == 0:
            return PublishingStatusCode.INACTIVE
        return PublishingStatusCode.ACTIVE

    def _extract_publication_date(self, raw_data: Dict) -> Optional[date]:
        """Extract publication date from year field."""
        # Try book_publication_year first
        year = raw_data.get("book_publication_year")
        if year:
            return self.safe_date(year)

        # Try book_year
        year = raw_data.get("book_year")
        if year:
            return self.safe_date(year)

        return None

    def _extract_contributors(
        self, raw_data: Dict, ctx: MappingContext
    ) -> List[ContributorDTO]:
        """Extract authors and other contributors."""
        contributors = []
        ctx.push("contributors")

        author_labels = raw_data.get("author_label", [])
        if not isinstance(author_labels, list):
            ctx.pop()
            return contributors

        for i, author in enumerate(author_labels):
            ctx.push(str(i))
            try:
                if isinstance(author, dict):
                    name = self.safe_str(author.get("label"))
                    if name:
                        contributors.append(
                            ContributorDTO(
                                role_code=ContributorRoleCode.AUTHOR,
                                sequence_number=i + 1,
                                contributor_type="P",
                                person_name=name,
                                person_name_inverted=None,
                                key_names=None,
                                names_before_key=None,
                                corporate_name=None,
                                biographical_note=None,
                                source_id=self.safe_str(author.get("option_id")),
                            )
                        )
            except Exception as e:
                ctx.add_warning("author", f"Failed to parse author: {e}")
            ctx.pop()

        # Extract translators if present
        translator_labels = raw_data.get("book_translator_label", [])
        if isinstance(translator_labels, list):
            for i, translator in enumerate(translator_labels):
                if isinstance(translator, dict):
                    name = self.safe_str(translator.get("label"))
                    if name:
                        contributors.append(
                            ContributorDTO(
                                role_code=ContributorRoleCode.TRANSLATOR,
                                sequence_number=len(contributors) + 1,
                                contributor_type="P",
                                person_name=name,
                                person_name_inverted=None,
                                key_names=None,
                                names_before_key=None,
                                corporate_name=None,
                                biographical_note=None,
                                source_id=self.safe_str(translator.get("option_id")),
                            )
                        )

        ctx.pop()
        return contributors

    def _extract_subjects(
        self, raw_data: Dict, ctx: MappingContext
    ) -> List[SubjectDTO]:
        """Extract categories and keywords."""
        subjects = []
        ctx.push("subjects")

        # Categories
        category_ids = raw_data.get("category_ids", [])
        if isinstance(category_ids, list):
            for i, cat_id in enumerate(category_ids[:10]):  # Limit to 10
                subjects.append(
                    SubjectDTO(
                        scheme_code=SubjectSchemeCode.PROPRIETARY,
                        subject_code=str(cat_id),
                        subject_heading_text=f"Yakaboo Category {cat_id}",
                        is_primary=(i == 0),
                        sequence_number=i + 1,
                    )
                )

        # Keywords - handle very long keyword strings (some have spam)
        keywords = raw_data.get("keywords")
        if keywords and isinstance(keywords, str):
            # Split and limit
            keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
            for i, kw_clean in enumerate(keyword_list[:20]):  # Limit to 20
                # Truncate if too long (max 500 chars)
                if len(kw_clean) > 500:
                    kw_clean = kw_clean[:497] + "..."
                subjects.append(
                    SubjectDTO(
                        scheme_code=SubjectSchemeCode.KEYWORDS,
                        subject_code=None,
                        subject_heading_text=kw_clean,
                        is_primary=False,
                        sequence_number=len(subjects) + 1,
                    )
                )

        ctx.pop()
        return subjects

    def _extract_text_content(
        self, raw_data: Dict, ctx: MappingContext
    ) -> List[TextContentDTO]:
        """Extract descriptions and other text content."""
        texts = []
        ctx.push("text_content")

        # Main description
        description = raw_data.get("description")
        if description and isinstance(description, str) and description.strip():
            texts.append(
                TextContentDTO(
                    text_type_code=TextTypeCode.MAIN_DESCRIPTION,
                    content=description,
                    author=None,
                    source_title=None,
                )
            )

        # Short description
        short_desc = raw_data.get("short_description")
        if short_desc and isinstance(short_desc, str) and short_desc.strip():
            # Only add if different from main description
            if not description or short_desc.strip() != description.strip():
                texts.append(
                    TextContentDTO(
                        text_type_code=TextTypeCode.SHORT_DESCRIPTION,
                        content=short_desc,
                        author=None,
                        source_title=None,
                    )
                )

        ctx.pop()
        return texts

    def _extract_media_files(
        self, raw_data: Dict, ctx: MappingContext
    ) -> List[MediaFileDTO]:
        """Extract images and other media."""
        media = []
        ctx.push("media_files")

        # Main image (string path)
        main_image = raw_data.get("image")
        if main_image and isinstance(main_image, str):
            media.append(
                MediaFileDTO(
                    resource_content_type_code="01",  # Front cover
                    resource_mode_code=ResourceModeCode.IMAGE,
                    file_format_code=None,
                    file_link=main_image,
                    width_px=None,
                    height_px=None,
                    file_size_bytes=None,
                    sequence_number=1,
                )
            )

        # Gallery images (list of dicts with 'file' or 'image_url' keys)
        gallery = raw_data.get("mediagallery_image", [])
        if isinstance(gallery, list):
            for i, item in enumerate(gallery[:10]):  # Limit to 10
                img_url = None
                if isinstance(item, str):
                    img_url = item
                elif isinstance(item, dict):
                    # Prefer full URL, fallback to file path
                    img_url = item.get("image_url") or item.get("file")

                if img_url and img_url != main_image:
                    media.append(
                        MediaFileDTO(
                            resource_content_type_code="02",  # Additional image
                            resource_mode_code=ResourceModeCode.IMAGE,
                            file_format_code=None,
                            file_link=img_url,
                            width_px=None,
                            height_px=None,
                            file_size_bytes=None,
                            sequence_number=len(media) + 1,
                        )
                    )

        ctx.pop()
        return media

    def _extract_prices(self, raw_data: Dict, ctx: MappingContext) -> List[PriceDTO]:
        """Extract price information."""
        prices = []
        ctx.push("prices")

        # Current price
        current_price = self.safe_decimal(raw_data.get("price"))
        if current_price and current_price > 0:
            original_price = self.safe_decimal(raw_data.get("original_price"))
            discount = None
            if original_price and original_price > current_price:
                discount = (
                    (original_price - current_price) / original_price * 100
                ).quantize(Decimal("0.01"))

            prices.append(
                PriceDTO(
                    source_code=self.source_code,
                    price_type_code=PriceTypeCode.RRP_INCL_TAX,
                    price_amount=current_price,
                    currency_code="UAH",
                    tax_rate_percent=None,
                    tax_amount=None,
                    price_effective_from=None,
                    price_effective_until=None,
                    discount_percent=discount,
                    original_price=original_price,
                    stock_quantity=None,
                    in_stock=raw_data.get("for_filter_is_in_stock") != "0",
                    recorded_at=datetime.utcnow(),
                )
            )

        ctx.pop()
        return prices
