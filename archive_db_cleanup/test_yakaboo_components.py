"""
Unit tests for low-level Yakaboo components: Settings, Mapper, Extractor.
"""
import pytest
from app.scraper.yakaboo import settings, mapper, extractor

# --- Settings Tests ---
def test_settings_constants():
    assert settings.SOURCE_CODE == "yakaboo"
    assert settings.RECORD_REFERENCE_PREFIX == "yakaboo_"
    assert settings.DEFAULT_CURRENCY == "UAH"

# --- Mapper Tests ---
def test_mapper_binding_codes():
    assert mapper.get_binding_code("Тверда") == "BB"
    assert mapper.get_binding_code("М'яка") == "BC"
    assert mapper.get_binding_code("Невідомо") == "BA" # Default to Book

def test_mapper_language_codes():
    assert mapper.get_lang_code("Українська") == "ukr"
    assert mapper.get_lang_code("Англійська") == "eng"
    assert mapper.get_lang_code("Chinese") == "ukr" # Default

# --- Extractor Tests (Legacy Parsers) ---
# Note: extractor.py (formerly parsers.py) might not have independent functions 
# exposed easily if it was class-based, but checking for simple helpers if any.
# Looking at the file content previously, it seemed to rely on helpers mostly.
# Let's test helpers via extractor if they are re-exported or used there.

# Actually, let's test helpers directly as they are crucial for extraction
from app.scraper.yakaboo.helpers import extract_label_value, normalize_string

def test_extract_label_value_complex():
    data = {
        "simple": "value",
        "complex_label": [{"label": "Target Value", "id": 1}],
        "empty_list": []
    }
    
    assert extract_label_value(data, "simple") == "value"
    assert extract_label_value(data, "complex") == "Target Value"
    assert extract_label_value(data, "missing") is None

def test_normalize_string():
    raw = "  Hello   World!  <br> "
    assert normalize_string(raw) == "Hello World!"
