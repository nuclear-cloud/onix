# app/adapters/yakaboo_native.py
"""
Адаптер для нативного Yakaboo каталогу (від бази 972k продуктів).
Структура відрізняється від Magento API - тут використовуються book_* поля.
"""
from typing import Dict, Any, List, Optional
from .base import BaseAdapter
from app.utils.mapper import safe_int, safe_float


class YakabooNativeAdapter(BaseAdapter):
    """Адаптер для нативного Yakaboo JSON формату."""
    
    def __init__(self):
        super().__init__(source_name="yakaboo_native")
        
        # Конфігурація ПОВНОГО мапінгу
        self.full_config = {
            "external_id": "id",
            "name": "name",
            "sku": "sku",
            "is_active": lambda src: src.get('status') != 'disabled',
            
            # Опис
            "description": lambda src: src.get('description'),
            "short_description": lambda src: src.get('short_description'),
            
            # Ціни
            "price": lambda src: safe_float(src.get('price')),
            "old_price": lambda src: safe_float(src.get('old_price')),
            "currency": lambda _: "UAH",
            
            # Медіа
            "main_image": lambda src: src.get('image'),
            "images": lambda src: [src.get('image')] if src.get('image') else [],
            
            # Книжні атрибути
            "isbn": lambda src: self._extract_isbn(src),
            "isbn13": lambda src: self._extract_isbn(src),
            "publisher": lambda src: self._extract_from_labels(src, 'book_publisher_label'),
            "author": lambda src: self._extract_from_labels(src, 'author_label'),
            "pages": lambda src: safe_int(src.get('book_page_count')),
            "year": lambda src: safe_int(src.get('book_publication_year')),
            "language": lambda src: self._map_language(src.get('book_lang')),
            "binding": lambda src: self._extract_from_labels(src, 'book_binding_label'),
            
            # Класифікація
            "thema_subject": lambda src: "F",  # Default - TODO: map categories
            "categories": lambda src: [],
            
            # URL та статус
            "url": lambda src: f"https://yakaboo.ua/{src.get('url_key', '')}",
            "in_stock": lambda src: src.get('for_filter_is_in_stock') != '0',
            
            # Дати
            "created_at": "created_at",
            "updated_at": "updated_at",
        }
        
        # Конфігурація ШВИДКОГО мапінгу
        self.market_config = {
            "sku": "sku",
            "isbn13": lambda src: self._extract_isbn(src),
            "price": lambda src: safe_float(src.get('price')),
            "old_price": lambda src: safe_float(src.get('old_price')),
            "currency": lambda _: "UAH",
            "in_stock": lambda src: src.get('for_filter_is_in_stock') != '0',
            "url": lambda src: f"https://yakaboo.ua/{src.get('url_key', '')}",
        }
    
    def _extract_isbn(self, src: Dict[str, Any]) -> Optional[str]:
        """Витягує ISBN-13."""
        # Спосіб 1: Пряме поле
        if 'book_isbn' in src:
            isbn = src['book_isbn']
            if isinstance(isbn, str) and isbn.strip():
                isbn_clean = isbn.replace('-', '').replace(' ', '')
                if len(isbn_clean) == 13 and isbn_clean.isdigit():
                    return isbn
        
        # Спосіб 2: Через label
        if 'book_isbn_label' in src:
            labels = src['book_isbn_label']
            if isinstance(labels, list) and labels:
                for label_obj in labels:
                    if isinstance(label_obj, dict):
                        isbn = label_obj.get('label', '')
                        if isbn and isinstance(isbn, str):
                            isbn_clean = isbn.replace('-', '').replace(' ', '')
                            if len(isbn_clean) == 13 and isbn_clean.isdigit():
                                return isbn
        
        return None
    
    def _extract_from_labels(self, src: Dict[str, Any], field: str) -> Optional[str]:
        """Витягує значення з label структури."""
        labels = src.get(f'{field}', [])
        
        if isinstance(labels, list) and labels:
            # Беремо першу label (найважливішу)
            label_obj = labels[0]
            if isinstance(label_obj, dict):
                return label_obj.get('label')
        
        return None
    
    def _map_language(self, lang_code: Optional[str]) -> str:
        """Картує код мови."""
        if not lang_code:
            return "ukr"
        
        lang_map = {
            '332272': 'ukr',  # Украинский
            '332273': 'rus',  # Русский
            '332271': 'eng',  # English
        }
        
        return lang_map.get(str(lang_code), "ukr")
    
    def parse_full(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Повний парсинг."""
        from app.utils.mapper import apply_mapping
        result = apply_mapping(raw_data, self.full_config)
        result["source"] = self.source_name
        return result
    
    def parse_market(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Швидкий парсинг (ціни)."""
        from app.utils.mapper import apply_mapping
        result = apply_mapping(raw_data, self.market_config)
        result["source"] = self.source_name
        return result
    
    def extract_isbn13(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Швидко дістає ISBN-13."""
        return self._extract_isbn(raw_data)
    
    def validate(self, raw_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Валідація."""
        errors = []
        warnings = []
        
        # Обов'язкові поля
        if not raw_data.get('id'):
            errors.append("Missing id")
        if not raw_data.get('name'):
            errors.append("Missing name")
        if not raw_data.get('sku'):
            errors.append("Missing sku")
        
        # Бажано мати ISBN
        if not self.extract_isbn13(raw_data):
            warnings.append("Missing ISBN")
        
        # Бажано бути книгою
        if not any(key in raw_data for key in ['book_isbn', 'book_page_count']):
            warnings.append("Not a book")
        
        all_messages = errors + warnings
        return len(errors) == 0, all_messages
