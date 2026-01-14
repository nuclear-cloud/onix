"""
Tests for ISBN/EAN Classifier.
"""

import pytest
from app.classifiers.isbn_classifier import (
    classify_item,
    extract_code_from_record,
    extract_price_from_record,
    normalize_isbn,
    ItemType,
    ItemStatus,
    ClassificationResult,
)


class TestNormalizeIsbn:
    """Tests for normalize_isbn function."""

    def test_isbn13_valid(self):
        """ISBN-13 should be returned as-is."""
        result = normalize_isbn("9789666023998")
        assert result == "9789666023998"

    def test_isbn10_to_13(self):
        """ISBN-10 should be converted to ISBN-13."""
        # 9668066332 (ISBN-10) -> 9789668066337 (ISBN-13)
        result = normalize_isbn("9668066332")
        assert result == "9789668066337"

    def test_isbn10_with_hyphens(self):
        """ISBN-10 with hyphens should be normalized."""
        result = normalize_isbn("966-80663-3-2")
        assert result == "9789668066337"

    def test_invalid_code(self):
        """Invalid code should return None."""
        assert normalize_isbn("4821234567890") is None  # EAN, not ISBN
        assert normalize_isbn("not-a-code") is None
        assert normalize_isbn(None) is None
        assert normalize_isbn("") is None


class TestClassifyItem:
    """Tests for classify_item function."""

    def test_ukrainian_book_978966(self):
        """Ukrainian books with 978-966 prefix."""
        result = classify_item("9789666023998")
        assert result.item_type == ItemType.BOOK_UA
        assert result.status == ItemStatus.NEW
        assert result.code == "9789666023998"

    def test_ukrainian_book_978617(self):
        """Ukrainian books with 978-617 prefix."""
        result = classify_item("9786177962297")
        assert result.item_type == ItemType.BOOK_UA
        assert result.status == ItemStatus.NEW

    def test_english_book_9780(self):
        """English books with 978-0 prefix."""
        result = classify_item("9780880034609")
        assert result.item_type == ItemType.BOOK_EN
        assert result.status == ItemStatus.NEW

    def test_english_book_9781(self):
        """English books with 978-1 prefix."""
        result = classify_item("9780316000000")
        assert result.item_type == ItemType.BOOK_EN
        assert result.status == ItemStatus.NEW

    def test_russian_book_9785(self):
        """Russian books with 978-5 prefix."""
        result = classify_item("9785045000123")
        assert result.item_type == ItemType.BOOK_RU
        assert result.status == ItemStatus.NEW

    def test_isbn10_converted(self):
        """ISBN-10 should be converted to ISBN-13."""
        # 9668066332 (ISBN-10) from Yakaboo data
        result = classify_item("9668066332")
        assert result.code == "9789668066337"
        assert result.status == ItemStatus.NEW

    def test_magazine_977(self):
        """Magazines with 977 prefix."""
        result = classify_item("9771234567001")
        assert result.item_type == ItemType.MAGAZINE
        assert result.status == ItemStatus.NEW

    def test_merch_ua_482(self):
        """Ukrainian merch with 482 prefix."""
        # Valid EAN-13 with correct checksum
        result = classify_item("4825000000005")
        assert result.item_type == ItemType.MERCH_UA
        assert result.status == ItemStatus.NEW

    def test_merch_cn_690(self):
        """Chinese merch with 690 prefix."""
        result = classify_item("6901234567892")  # Valid checksum
        assert result.item_type == ItemType.MERCH_CN
        assert result.status == ItemStatus.NEW

    def test_merch_other(self):
        """Other merch."""
        result = classify_item("4006381333931")  # Valid checksum
        assert result.item_type == ItemType.MERCH_OTHER
        assert result.status == ItemStatus.NEW

    def test_invalid_empty_string(self):
        """Empty string."""
        result = classify_item("")
        assert result.item_type == ItemType.INVALID
        assert result.status == ItemStatus.NOCODE

    def test_invalid_none(self):
        """None input."""
        result = classify_item(None)
        assert result.item_type == ItemType.INVALID
        assert result.status == ItemStatus.NOCODE

    def test_invalid_random_string(self):
        """Random invalid string."""
        result = classify_item("not-a-barcode")
        assert result.item_type == ItemType.INVALID
        assert result.status == ItemStatus.NOCODE

    def test_to_dict_method(self):
        """Test to_dict()."""
        result = classify_item("9789666023998")
        d = result.to_dict()
        assert "code" in d
        assert "item_type" in d
        assert "status" in d
        assert d["item_type"] == "BOOK_UA"
        assert d["status"] == "NEW"


class TestExtractCodeFromRecord:
    """Tests for extract_code_from_record function."""

    def test_from_barcode(self):
        """Extract from barcode field."""
        record = {"barcode": "9789666023998"}
        assert extract_code_from_record(record) == "9789666023998"

    def test_from_book_isbn(self):
        """Extract from book_isbn field (ISBN-10)."""
        record = {"book_isbn": "9668066332"}  # ISBN-10
        assert extract_code_from_record(record) == "9789668066337"  # Converted to 13

    def test_from_book_isbn_label(self):
        """Extract from book_isbn_label array."""
        record = {
            "book_isbn_label": [
                {"label": "978-5-045-000-12-3"},
            ]
        }
        assert extract_code_from_record(record) == "9785045000123"

    def test_no_code(self):
        """Return None when no code."""
        record = {"sku": "12345"}
        assert extract_code_from_record(record) is None

    def test_invalid_barcode(self):
        """Return None for invalid barcode."""
        record = {"barcode": "not-a-code"}
        assert extract_code_from_record(record) is None


class TestExtractPriceFromRecord:
    """Tests for extract_price_from_record function."""

    def test_from_price_info(self):
        """Extract from price_info."""
        record = {"price_info": {"final_price": "299.00"}}
        assert extract_price_from_record(record) == 299.00

    def test_from_custom_attributes(self):
        """Extract from custom_attributes."""
        record = {
            "custom_attributes": [
                {"attribute_code": "price", "value": "150.50"},
            ]
        }
        assert extract_price_from_record(record) == 150.50

    def test_no_price(self):
        """Return None when no price."""
        record = {"sku": "12345"}
        assert extract_price_from_record(record) is None

    def test_invalid_price(self):
        """Return None for invalid price."""
        record = {"price_info": {"final_price": "not-a-price"}}
        assert extract_price_from_record(record) is None
