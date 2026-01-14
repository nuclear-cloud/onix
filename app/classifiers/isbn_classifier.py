"""
ISBN/EAN Classifier for Smart Gatekeeper System.
Handles ISBN-10 to ISBN-13 conversion and EAN validation.
"""

from stdnum import isbn, ean
from stdnum.util import clean
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ItemType(Enum):
    """Item types with country/region."""

    BOOK_UA = "BOOK_UA"
    BOOK_EN = "BOOK_EN"
    BOOK_RU = "BOOK_RU"
    BOOK_DE = "BOOK_DE"
    BOOK_PL = "BOOK_PL"
    BOOK_OTHER = "BOOK_OTHER"
    MAGAZINE = "MAGAZINE"
    MUSIC = "MUSIC"
    MERCH_UA = "MERCH_UA"
    MERCH_CN = "MERCH_CN"
    MERCH_OTHER = "MERCH_OTHER"
    INVALID = "INVALID"


class ItemStatus(Enum):
    """Processing status."""

    NEW = "NEW"
    NOCODE = "NOCODE"
    PROCESSED = "PROCESSED"


@dataclass
class ClassificationResult:
    """Classification result."""

    code: Optional[str]
    item_type: ItemType
    status: ItemStatus

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "item_type": self.item_type.value,
            "status": self.status.value,
        }


def normalize_isbn(code: str) -> Optional[str]:
    """
    Normalize ISBN to ISBN-13 format.
    Handles both ISBN-10 and ISBN-13.
    Returns None if invalid.
    """
    if not code:
        return None

    code = clean(str(code))

    # Remove any hyphens
    code = code.replace("-", "").replace(" ", "")

    # Check if it's already a valid ISBN-13
    if len(code) == 13 and code.isdigit() and isbn.is_valid(code):
        return code

    # Check if it's a valid ISBN-10 and convert to ISBN-13
    if len(code) == 10 and code[:-1].isdigit():
        if isbn.is_valid(code):
            # Convert ISBN-10 to ISBN-13
            # Prefix 978 + first 9 digits of ISBN-10 + calculated check digit
            prefix = "978" + code[:-1]

            # Calculate check digit for ISBN-13 (weights 1, 3, 1, 3...)
            total = 0
            for i, digit in enumerate(prefix):
                weight = 1 if i % 2 == 0 else 3
                total += int(digit) * weight

            remainder = total % 10
            check_digit = 0 if remainder == 0 else 10 - remainder

            return prefix + str(check_digit)

    # Check if it's a valid ISBN-13
    if len(code) == 13 and code.isdigit() and isbn.is_valid(code):
        return code

    return None


def classify_item(raw_code: str | None) -> ClassificationResult:
    """
    Classify item by barcode.
    Handles ISBN-10 to ISBN-13 conversion.
    """
    if not raw_code or not str(raw_code).strip():
        return ClassificationResult(
            code=None,
            item_type=ItemType.INVALID,
            status=ItemStatus.NOCODE,
        )

    code = clean(str(raw_code))

    # --- 1. CHECK FOR ISBN (978/979 or 10-digit) ---
    # First try as ISBN-13 or ISBN-10
    normalized = normalize_isbn(code)
    if normalized:
        # Check if it's music scores (979-0...)
        if normalized.startswith("9790"):
            return ClassificationResult(
                code=normalized,
                item_type=ItemType.MUSIC,
                status=ItemStatus.NEW,
            )

        # Determine region by ISBN-13 prefix
        if normalized.startswith("978966") or normalized.startswith("978617"):
            return ClassificationResult(
                code=normalized,
                item_type=ItemType.BOOK_UA,
                status=ItemStatus.NEW,
            )

        if normalized.startswith("9780") or normalized.startswith("9781"):
            return ClassificationResult(
                code=normalized,
                item_type=ItemType.BOOK_EN,
                status=ItemStatus.NEW,
            )

        if normalized.startswith("9785"):
            return ClassificationResult(
                code=normalized,
                item_type=ItemType.BOOK_RU,
                status=ItemStatus.NEW,
            )

        if normalized.startswith("9783"):
            return ClassificationResult(
                code=normalized,
                item_type=ItemType.BOOK_DE,
                status=ItemStatus.NEW,
            )

        if normalized.startswith("97883"):
            return ClassificationResult(
                code=normalized,
                item_type=ItemType.BOOK_PL,
                status=ItemStatus.NEW,
            )

        # Other 978/979 books
        return ClassificationResult(
            code=normalized,
            item_type=ItemType.BOOK_OTHER,
            status=ItemStatus.NEW,
        )

    # --- 2. CHECK FOR MAGAZINES (ISSN 977...) ---
    if code.startswith("977"):
        return ClassificationResult(
            code=code,
            item_type=ItemType.MAGAZINE,
            status=ItemStatus.NEW,
        )

    # --- 3. CHECK FOR MERCH (EAN-13) ---
    if ean.is_valid(code):
        if code.startswith("482"):
            return ClassificationResult(
                code=code,
                item_type=ItemType.MERCH_UA,
                status=ItemStatus.NEW,
            )
        if code.startswith("690") or code.startswith("699"):
            return ClassificationResult(
                code=code,
                item_type=ItemType.MERCH_CN,
                status=ItemStatus.NEW,
            )
        return ClassificationResult(
            code=code,
            item_type=ItemType.MERCH_OTHER,
            status=ItemStatus.NEW,
        )

    # --- 4. UNKNOWN CODE ---
    return ClassificationResult(
        code=None,
        item_type=ItemType.INVALID,
        status=ItemStatus.NOCODE,
    )


def extract_code_from_record(record: dict) -> Optional[str]:
    """
    Extract and normalize ISBN/EAN from Yakaboo record.
    Returns ISBN-13 for valid ISBNs (10 or 13), EAN for others.
    """
    # Method 1: barcode field
    barcode = record.get("barcode")
    if barcode:
        # Try ISBN first
        normalized = normalize_isbn(barcode)
        if normalized:
            return normalized
        # Try EAN
        code = clean(str(barcode))
        if ean.is_valid(code):
            return code

    # Method 2: book_isbn field
    isbn_field = record.get("book_isbn")
    if isbn_field:
        normalized = normalize_isbn(isbn_field)
        if normalized:
            return normalized

    # Method 3: book_isbn_label array
    isbn_labels = record.get("book_isbn_label", [])
    if isinstance(isbn_labels, list):
        for item in isbn_labels:
            if isinstance(item, dict):
                label = item.get("label", "")
                if label:
                    normalized = normalize_isbn(label)
                    if normalized:
                        return normalized

    return None


def extract_price_from_record(record: dict) -> Optional[float]:
    """Extract price from Yakaboo record."""
    # Method 1: final_price (most common)
    final_price = record.get("final_price")
    if final_price:
        try:
            return float(final_price)
        except (ValueError, TypeError):
            pass

    # Method 2: price field
    price = record.get("price")
    if price:
        try:
            return float(price)
        except (ValueError, TypeError):
            pass

    # Method 3: regular_price
    regular_price = record.get("regular_price")
    if regular_price:
        try:
            return float(regular_price)
        except (ValueError, TypeError):
            pass

    return None
