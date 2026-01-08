# tests/test_yakaboo_import.py
"""
Тести для Yakaboo імпортера.
"""
import json
import pytest
from app.services.yakaboo_import import (
    map_yakaboo_product,
    extract_isbn13,
    validate_yakaboo_product,
    map_yakaboo_batch,
)
from app.utils.mapper import (
    get_deep_value,
    find_attribute,
    map_thema_subject,
)


# --- Фікстури ---

@pytest.fixture
def fake_yakaboo_response():
    """Симуляція відповіді від Yakaboo API."""
    return {
        "entity_id": 555,
        "sku": "BOOK-999",
        "name": "Дюна",
        "status": 1,
        "created_at": "2024-01-01T10:00:00",
        "updated_at": "2024-12-01T15:30:00",
        "price_info": {
            "final_price": 600.00,
            "regular_price": 750.00
        },
        "media_gallery_entries": [
            {"file": "/media/catalog/product/d/u/dune_cover.jpg"},
            {"file": "/media/catalog/product/d/u/dune_back.jpg"}
        ],
        "categories": [
            {"id": 1, "name": "Книги"},
            {"id": 2, "name": "Художня література"},
            {"id": 3, "name": "Фантастика"}
        ],
        "custom_attributes": [
            {"attribute_code": "isbn", "value": "978-0441172719"},
            {"attribute_code": "isbn13", "value": "978-0441172719"},
            {"attribute_code": "publisher_name", "value": "КСД"},
            {"attribute_code": "author", "value": "Френк Герберт"},
            {"attribute_code": "page_count", "value": "896"},
            {"attribute_code": "publication_year", "value": "2019"},
            {"attribute_code": "language", "value": "ukr"},
            {"attribute_code": "binding_type", "value": "тверда"},
            {"attribute_code": "description", "value": "Епічна історія про пустельну планету Арракіс..."},
            {"attribute_code": "stock_status", "value": "in_stock"},
        ]
    }


@pytest.fixture
def minimal_yakaboo_response():
    """Мінімальні обов'язкові поля."""
    return {
        "entity_id": 123,
        "sku": "MIN-001",
        "name": "Тестова книга",
        "status": 0,
    }


# --- Тести утиліт ---

def test_get_deep_value():
    """Тест витягування значень з глибоких структур."""
    data = {
        "price_info": {
            "final_price": 100.50
        },
        "items": [
            {"name": "First"},
            {"name": "Second"}
        ]
    }
    
    assert get_deep_value(data, "price_info.final_price") == 100.50
    assert get_deep_value(data, "items.0.name") == "First"
    assert get_deep_value(data, "items.1.name") == "Second"
    assert get_deep_value(data, "missing.field") is None
    assert get_deep_value(data, "items.99.name") is None


def test_find_attribute():
    """Тест пошуку атрибутів."""
    attributes = [
        {"attribute_code": "isbn", "value": "978-123"},
        {"attribute_code": "author", "value": "Шевченко"},
    ]
    
    assert find_attribute(attributes, "isbn") == "978-123"
    assert find_attribute(attributes, "author") == "Шевченко"
    assert find_attribute(attributes, "missing") is None
    assert find_attribute([], "isbn") is None
    assert find_attribute(None, "isbn") is None


def test_map_thema_subject():
    """Тест мапінгу категорій в THEMA коди."""
    # Фантастика
    categories = [
        {"id": 1, "name": "Книги"},
        {"id": 2, "name": "Художня література"},
        {"id": 3, "name": "Фантастика"}
    ]
    assert map_thema_subject(categories) == "FBA"
    
    # Детективи
    categories = [{"id": 1, "name": "Детективи"}]
    assert map_thema_subject(categories) == "FF"
    
    # Невідома категорія → дефолт
    categories = [{"id": 999, "name": "Невідома категорія"}]
    assert map_thema_subject(categories) == "F"  # Default
    
    # Порожній список → дефолт
    assert map_thema_subject([]) == "F"


# --- Тести мапінгу ---

def test_map_yakaboo_product_full(fake_yakaboo_response):
    """Тест повного мапінгу продукту."""
    result = map_yakaboo_product(fake_yakaboo_response)
    
    # Базові поля
    assert result["external_id"] == 555
    assert result["name"] == "Дюна"
    assert result["sku"] == "BOOK-999"
    assert result["is_active"] is True
    
    # Ціни
    assert result["price"] == 600.00
    assert result["old_price"] == 750.00
    assert result["currency"] == "UAH"
    
    # Медіа
    assert "/dune_cover.jpg" in result["main_image"]
    assert len(result["images"]) == 2
    
    # Атрибути книги
    assert result["isbn"] == "978-0441172719"
    assert result["isbn13"] == "978-0441172719"
    assert result["publisher"] == "КСД"
    assert result["author"] == "Френк Герберт"
    assert result["pages"] == 896
    assert result["year"] == 2019
    assert result["language"] == "ukr"
    assert result["binding"] == "тверда"
    
    # THEMA
    assert result["thema_subject"] == "FBA"  # Фантастика
    
    # Категорії
    assert len(result["categories"]) == 3
    
    # URL
    assert "yakaboo.ua" in result["url"]
    assert "BOOK-999" in result["url"]
    
    # Наявність
    assert result["in_stock"] is True


def test_map_yakaboo_product_minimal(minimal_yakaboo_response):
    """Тест мапінгу з мінімальними даними."""
    result = map_yakaboo_product(minimal_yakaboo_response)
    
    assert result["external_id"] == 123
    assert result["name"] == "Тестова книга"
    assert result["is_active"] is False  # status = 0
    assert result["currency"] == "UAH"  # Завжди є
    assert result["price"] is None  # Не вказано
    assert result["isbn"] is None


def test_extract_isbn13(fake_yakaboo_response):
    """Тест швидкого витягування ISBN."""
    isbn = extract_isbn13(fake_yakaboo_response)
    assert isbn == "978-0441172719"
    
    # Без ISBN
    empty = {"custom_attributes": []}
    assert extract_isbn13(empty) is None


def test_validate_yakaboo_product(fake_yakaboo_response, minimal_yakaboo_response):
    """Тест валідації продуктів."""
    # Повний продукт - валідний
    is_valid, errors = validate_yakaboo_product(fake_yakaboo_response)
    assert is_valid is True
    assert len(errors) == 0
    
    # Мінімальний продукт - валідний, але без ISBN (warning)
    is_valid, errors = validate_yakaboo_product(minimal_yakaboo_response)
    assert is_valid is True  # Warning не блокує
    assert any("ISBN" in err for err in errors)
    
    # Невалідний - без обов'язкових полів
    invalid = {}
    is_valid, errors = validate_yakaboo_product(invalid)
    assert is_valid is False
    assert len(errors) >= 3  # entity_id, name, sku


def test_map_yakaboo_batch(fake_yakaboo_response, minimal_yakaboo_response):
    """Тест обробки декількох продуктів."""
    products = [fake_yakaboo_response, minimal_yakaboo_response]
    results = map_yakaboo_batch(products)
    
    assert len(results) == 2
    assert results[0]["name"] == "Дюна"
    assert results[1]["name"] == "Тестова книга"


# --- Тести крайніх випадків ---

def test_thema_mapping_priority():
    """Тест пріоритетності категорій (найглибша виграє)."""
    categories = [
        {"id": 1, "name": "Книги"},  # Немає в THEMA_MAP
        {"id": 2, "name": "Художня література"},  # F
        {"id": 3, "name": "Детективи"}  # FF - це має виграти
    ]
    assert map_thema_subject(categories) == "FF"


def test_empty_media_gallery():
    """Тест коли немає зображень."""
    data = {"media_gallery_entries": []}
    result = map_yakaboo_product(data)
    assert result["main_image"] is None
    assert result["images"] == []


def test_missing_price_info():
    """Тест коли немає цін."""
    data = {"entity_id": 1, "name": "Test", "sku": "T1"}
    result = map_yakaboo_product(data)
    assert result["price"] is None
    assert result["old_price"] is None


def test_invalid_numeric_values():
    """Тест коли числові поля мають невалідні значення."""
    data = {
        "entity_id": 1,
        "name": "Test",
        "sku": "T1",
        "custom_attributes": [
            {"attribute_code": "page_count", "value": "not-a-number"},
            {"attribute_code": "publication_year", "value": "invalid"},
        ]
    }
    result = map_yakaboo_product(data)
    assert result["pages"] is None
    assert result["year"] is None


# --- Demo функція для ручного запуску ---

def demo_import():
    """
    Демонстрація роботи імпортера.
    Запустіть: python -m pytest tests/test_yakaboo_import.py::demo_import -s
    """
    fake_api_response = {
        "entity_id": 555,
        "sku": "BOOK-999",
        "name": "Дюна",
        "status": 1,
        "price_info": {"final_price": 600.00, "regular_price": 750.00},
        "media_gallery_entries": [{"file": "dune_cover.jpg"}],
        "categories": [
            {"id": 1, "name": "Книги"},
            {"id": 2, "name": "Художня література"},
            {"id": 3, "name": "Фантастика"}
        ],
        "custom_attributes": [
            {"attribute_code": "isbn", "value": "978-0441172719"},
            {"attribute_code": "publisher_name", "value": "КСД"},
            {"attribute_code": "author", "value": "Френк Герберт"},
        ]
    }
    
    clean_data = map_yakaboo_product(fake_api_response)
    
    print("\n" + "="*60)
    print("🔥 YAKABOO IMPORT DEMO")
    print("="*60)
    print(json.dumps(clean_data, indent=2, ensure_ascii=False))
    print("="*60)
    print(f"✅ THEMA Code: {clean_data['thema_subject']}")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Запуск демо
    demo_import()
