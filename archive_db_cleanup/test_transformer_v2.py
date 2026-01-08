import sys
import os
sys.path.append(os.getcwd())

import pytest
from app.scraper.yakaboo.enrichment_transformer import yakaboo_to_onix_v2
from app.schemas.onix_full import OnixProduct

@pytest.fixture
def raw_yakaboo_item():
    return {
        "id": 12345,
        "name": "Test Book Title",
        "book_isbn": "978-617-1234-56-7",
        "book_publisher_label": [{"label": "Vivat"}],
        "author_label": [{"label": "John Doe"}],
        "price": 100.50,
        "book_page_count": "300",
        "sku": "SKU123"
    }

def test_transform_basic_fields(raw_yakaboo_item):
    """Test that basic fields are mapped correctly to ONIX model."""
    result = yakaboo_to_onix_v2(raw_yakaboo_item)
    
    assert isinstance(result, OnixProduct)
    assert result.record_reference == "yakaboo_12345"
    
    # Titles (ONIX 3.0 Structure)
    assert len(result.title_detail) > 0
    # Accessing deep structure: TitleDetail -> TitleElement -> TitleText
    title_text = result.title_detail[0].title_element[0].title_text
    assert title_text == "Test Book Title"
    
    # ISBN (Product Identifier Type 15 = ISBN-13)
    isbn_ids = [id.id_value for id in result.product_identifier if id.product_id_type == "15"]
    assert "9786171234567" in isbn_ids
    
    # SKU (Assuming Proprietary or GTIN logic from transformer)
    # Extra check for SKU in extras usually
    assert result.extra.get("source_sku") == "SKU123"

def test_transform_contributors(raw_yakaboo_item):
    """Test author transformation."""
    result = yakaboo_to_onix_v2(raw_yakaboo_item)
    
    # Role A01 = By (author)
    authors = [c.person_name for c in result.contributor if "A01" in c.contributor_role]
    assert "John Doe" in authors

def test_transform_publisher(raw_yakaboo_item):
    """Test publisher transformation."""
    result = yakaboo_to_onix_v2(raw_yakaboo_item)
    
    publishers = [p.publisher_name for p in result.publisher]
    assert "Vivat" in publishers

def test_transform_extents(raw_yakaboo_item):
    """Test page count."""
    result = yakaboo_to_onix_v2(raw_yakaboo_item)
    
    # Type 00 (Main Content) or 03 (Pages) depending on mapping. V2 uses specific types.
    # Looking at enrichment_transformer.py logic for "extent_pages":
    # It maps to ExtentType.MAIN_PAGE_COUNT which is usually a code.
    # Let's check if any extent has value 300
    
    pages = [e.extent_value for e in result.extent]
    assert 300.0 in pages

def test_invalid_input_graceful_handling():
    """Test that transformer handles partial/bad data without crashing."""
    bad_data = {
        "id": "abc",
        # Missing name, ISBN, etc.
    }
    result = yakaboo_to_onix_v2(bad_data)
    
    assert result.record_reference == "yakaboo_abc"
    # Should maintain basic validity even if empty
    assert isinstance(result, OnixProduct)