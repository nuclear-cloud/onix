# services/yakaboo_import.py
"""
Конфігурація мапінгу для імпорту даних з Yakaboo API.
"""
from typing import Dict, List, Optional
from app.utils.mapper import (
    apply_mapping,
    find_attribute,
    map_thema_subject,
    extract_first_image,
    safe_int,
    safe_float,
)


# Правила мапінгу Yakaboo → Наша структура
YAKABOO_CONFIG = {
    # --- Базові поля ---
    "external_id": "entity_id",
    "name": "name",
    "sku": "sku",
    "is_active": lambda src: src.get('status') == 1,
    
    # --- Опис ---
    "description": lambda src: find_attribute(
        src.get('custom_attributes', []), 
        'description'
    ),
    "short_description": lambda src: find_attribute(
        src.get('custom_attributes', []), 
        'short_description'
    ),
    
    # --- Ціни ---
    "price": lambda src: safe_float(src.get('price_info', {}).get('final_price')),
    "old_price": lambda src: safe_float(src.get('price_info', {}).get('regular_price')),
    "currency": lambda _: "UAH",  # Завжди гривня
    
    # --- Медіа (Картинки) ---
    "main_image": lambda src: extract_first_image(src.get('media_gallery_entries', [])),
    "images": lambda src: [
        img.get('file') 
        for img in src.get('media_gallery_entries', [])
        if img.get('file')
    ],
    
    # --- Атрибути книги (через custom_attributes) ---
    "isbn": lambda src: find_attribute(src.get('custom_attributes', []), 'isbn'),
    "isbn13": lambda src: find_attribute(src.get('custom_attributes', []), 'isbn13') or 
                          find_attribute(src.get('custom_attributes', []), 'isbn'),
    "publisher": lambda src: find_attribute(
        src.get('custom_attributes', []), 
        'publisher_name'
    ),
    "author": lambda src: find_attribute(src.get('custom_attributes', []), 'author'),
    "pages": lambda src: safe_int(
        find_attribute(src.get('custom_attributes', []), 'page_count')
    ),
    "year": lambda src: safe_int(
        find_attribute(src.get('custom_attributes', []), 'publication_year')
    ),
    "language": lambda src: find_attribute(
        src.get('custom_attributes', []), 
        'language'
    ) or "ukr",  # Дефолт українська
    "binding": lambda src: find_attribute(
        src.get('custom_attributes', []), 
        'binding_type'
    ),
    "weight": lambda src: safe_float(
        find_attribute(src.get('custom_attributes', []), 'weight')
    ),
    "dimensions": lambda src: find_attribute(
        src.get('custom_attributes', []), 
        'dimensions'
    ),
    
    # --- THEMA Subject (Найцікавіше) ---
    "thema_subject": lambda src: map_thema_subject(src.get('categories', [])),
    
    # --- Категорії (сирі дані для аналізу) ---
    "categories": lambda src: [
        {"id": cat.get("id"), "name": cat.get("name")}
        for cat in src.get('categories', [])
    ],
    
    # --- URL ---
    "url": lambda src: f"https://yakaboo.ua/ua/{src.get('sku', '')}.html",
    
    # --- Наявність ---
    "in_stock": lambda src: find_attribute(
        src.get('custom_attributes', []), 
        'stock_status'
    ) == 'in_stock',
    
    # --- Дата додавання ---
    "created_at": "created_at",
    "updated_at": "updated_at",
}


def map_yakaboo_product(raw_json: dict) -> dict:
    """
    Трансформує сирий JSON від Yakaboo API в нашу структуру.
    
    Args:
        raw_json: Сирі дані від Yakaboo (Magento 2 format)
        
    Returns:
        Очищений словник з нашими полями
        
    Example:
        >>> raw = {"entity_id": 123, "name": "Дюна", ...}
        >>> clean = map_yakaboo_product(raw)
        >>> print(clean["name"])
        "Дюна"
    """
    return apply_mapping(raw_json, YAKABOO_CONFIG)


def map_yakaboo_batch(products: List[dict]) -> List[dict]:
    """
    Обробляє список продуктів.
    
    Args:
        products: Список сирих JSON об'єктів
        
    Returns:
        Список очищених продуктів
    """
    return [map_yakaboo_product(product) for product in products]


def extract_isbn13(raw_json: dict) -> Optional[str]:
    """
    Швидко витягує ISBN-13 без повного мапінгу.
    Корисно для початкової валідації.
    
    Args:
        raw_json: Сирі дані від Yakaboo
        
    Returns:
        ISBN-13 або None
    """
    attrs = raw_json.get('custom_attributes', [])
    return (
        find_attribute(attrs, 'isbn13') or
        find_attribute(attrs, 'isbn')
    )


def validate_yakaboo_product(raw_json: dict) -> tuple[bool, List[str]]:
    """
    Перевіряє чи JSON від Yakaboo валідний для імпорту.
    
    Args:
        raw_json: Сирі дані від Yakaboo
        
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    warnings = []
    
    # Обов'язкові поля
    if not raw_json.get('entity_id'):
        errors.append("Missing entity_id")
    if not raw_json.get('name'):
        errors.append("Missing name")
    if not raw_json.get('sku'):
        errors.append("Missing sku")
        
    # Бажано мати ISBN (warning, не блокує)
    if not extract_isbn13(raw_json):
        warnings.append("Missing ISBN (warning)")
        
    # Повертаємо всі повідомлення, але валідність залежить тільки від errors
    all_messages = errors + warnings
    return len(errors) == 0, all_messages
