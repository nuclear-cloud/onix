# app/adapters/yakaboo.py
"""
Адаптер для Yakaboo (Magento 2 API).
"""
from typing import Dict, Any, List, Optional
from .base import BaseAdapter
from app.utils.mapper import (
    apply_mapping,
    find_attribute,
    map_thema_subject,
    extract_first_image,
    safe_int,
    safe_float,
)


class YakabooAdapter(BaseAdapter):
    """Адаптер для Yakaboo - вміє розбирати їх складний JSON."""
    
    def __init__(self):
        super().__init__(source_name="yakaboo")
        
        # Конфігурація ПОВНОГО мапінгу
        self.full_config = {
            "external_id": "entity_id",
            "name": "name",
            "sku": "sku",
            "is_active": lambda src: src.get('status') == 1,
            "description": lambda src: find_attribute(
                src.get('custom_attributes', []), 'description'
            ),
            "short_description": lambda src: find_attribute(
                src.get('custom_attributes', []), 'short_description'
            ),
            "price": lambda src: safe_float(src.get('price_info', {}).get('final_price')),
            "old_price": lambda src: safe_float(src.get('price_info', {}).get('regular_price')),
            "currency": lambda _: "UAH",
            "main_image": lambda src: extract_first_image(src.get('media_gallery_entries', [])),
            "images": lambda src: [
                img.get('file') for img in src.get('media_gallery_entries', [])
                if img.get('file')
            ],
            "isbn": lambda src: find_attribute(src.get('custom_attributes', []), 'isbn'),
            "isbn13": lambda src: (
                find_attribute(src.get('custom_attributes', []), 'isbn13') or
                find_attribute(src.get('custom_attributes', []), 'isbn')
            ),
            "publisher": lambda src: find_attribute(
                src.get('custom_attributes', []), 'publisher_name'
            ),
            "author": lambda src: find_attribute(
                src.get('custom_attributes', []), 'author'
            ),
            "pages": lambda src: safe_int(
                find_attribute(src.get('custom_attributes', []), 'page_count')
            ),
            "year": lambda src: safe_int(
                find_attribute(src.get('custom_attributes', []), 'publication_year')
            ),
            "language": lambda src: find_attribute(
                src.get('custom_attributes', []), 'language'
            ) or "ukr",
            "binding": lambda src: find_attribute(
                src.get('custom_attributes', []), 'binding_type'
            ),
            "weight": lambda src: safe_float(
                find_attribute(src.get('custom_attributes', []), 'weight')
            ),
            "dimensions": lambda src: find_attribute(
                src.get('custom_attributes', []), 'dimensions'
            ),
            "thema_subject": lambda src: map_thema_subject(src.get('categories', [])),
            "categories": lambda src: [
                {"id": cat.get("id"), "name": cat.get("name")}
                for cat in src.get('categories', [])
            ],
            "url": lambda src: f"https://yakaboo.ua/ua/{src.get('sku', '')}.html",
            "in_stock": lambda src: find_attribute(
                src.get('custom_attributes', []), 'stock_status'
            ) == 'in_stock',
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
        
        # Конфігурація ШВИДКОГО мапінгу (тільки ціни)
        self.market_config = {
            "sku": "sku",
            "isbn13": lambda src: (
                find_attribute(src.get('custom_attributes', []), 'isbn13') or
                find_attribute(src.get('custom_attributes', []), 'isbn')
            ),
            "price": lambda src: safe_float(src.get('price_info', {}).get('final_price')),
            "old_price": lambda src: safe_float(src.get('price_info', {}).get('regular_price')),
            "currency": lambda _: "UAH",
            "in_stock": lambda src: find_attribute(
                src.get('custom_attributes', []), 'stock_status'
            ) == 'in_stock',
            "url": lambda src: f"https://yakaboo.ua/ua/{src.get('sku', '')}.html",
        }
    
    def parse_full(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Повний парсинг: всі поля.
        Використовується для щоденного імпорту каталогу.
        """
        result = apply_mapping(raw_data, self.full_config)
        result["source"] = self.source_name
        return result
    
    def parse_market(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Швидкий парсинг: тільки ціни та наявність.
        Використовується для погодинного оновлення.
        """
        result = apply_mapping(raw_data, self.market_config)
        result["source"] = self.source_name
        return result
    
    def extract_isbn13(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Швидко дістає ISBN-13."""
        attrs = raw_data.get('custom_attributes', [])
        return (
            find_attribute(attrs, 'isbn13') or
            find_attribute(attrs, 'isbn')
        )
    
    def validate(self, raw_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Валідація даних Yakaboo."""
        errors = []
        warnings = []
        
        # Обов'язкові поля
        if not raw_data.get('entity_id'):
            errors.append("Missing entity_id")
        if not raw_data.get('name'):
            errors.append("Missing name")
        if not raw_data.get('sku'):
            errors.append("Missing sku")
        
        # Бажано мати ISBN (warning)
        if not self.extract_isbn13(raw_data):
            warnings.append("Missing ISBN")
        
        all_messages = errors + warnings
        return len(errors) == 0, all_messages
    
    def parse_batch_full(self, products: List[Dict]) -> List[Dict]:
        """Обробка списку продуктів (повний режим)."""
        return [self.parse_full(p) for p in products]
    
    def parse_batch_market(self, products: List[Dict]) -> List[Dict]:
        """Обробка списку продуктів (швидкий режим)."""
        return [self.parse_market(p) for p in products]
