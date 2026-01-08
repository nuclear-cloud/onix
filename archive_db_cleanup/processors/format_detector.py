"""
Format Detector

Визначає формат даних у JSONL файлах для автоматичного вибору трансформера.
"""
from typing import Dict, Any, Optional, List
import re


class FormatDetector:
    """Визначає формат даних на основі структури JSON."""
    
    # Ключові поля для визначення формату
    YAKABOO_MARKERS = [
        "book_isbn", "book_isbn_label", "book_binding_type", 
        "book_publisher", "author_label", "url_key"
    ]
    
    VIVAT_MARKERS = [
        "vivat_id", "vivat_sku", "publisher_name", 
        "attributes", "product_url"
    ]
    
    GENERIC_MARKERS = [
        "isbn", "isbn13", "isbn_13", "title", "name",
        "author", "authors", "publisher"
    ]
    
    @staticmethod
    def detect_format(data: Dict[str, Any]) -> str:
        """
        Визначає формат даних.
        
        Returns:
            'yakaboo', 'vivat', 'generic', 'onix', 'unknown'
        """
        if not isinstance(data, dict):
            return "unknown"
        
        keys = set(data.keys())
        key_lower = {k.lower() for k in keys}
        
        # Перевірка ONIX формату
        if any(k in keys for k in ["product_identifier", "titles", "contributors", "onix_version"]):
            return "onix"
        
        # Перевірка Yakaboo формату
        yakaboo_score = sum(1 for m in FormatDetector.YAKABOO_MARKERS if m in keys)
        if yakaboo_score >= 3:
            return "yakaboo"
        
        # Перевірка Vivat формату
        vivat_score = sum(1 for m in FormatDetector.VIVAT_MARKERS if m in keys)
        if vivat_score >= 2:
            return "vivat"
        
        # Перевірка generic формату
        generic_score = sum(1 for m in FormatDetector.GENERIC_MARKERS if m in key_lower)
        if generic_score >= 3:
            return "generic"
        
        return "unknown"
    
    @staticmethod
    def extract_isbn(data: Dict[str, Any]) -> Optional[str]:
        """Витягує ISBN з даних різних форматів."""
        # Yakaboo формат
        isbn = data.get("book_isbn") or data.get("book_isbn_label")
        if isbn:
            return FormatDetector._clean_isbn(str(isbn))
        
        # Vivat формат
        isbn = data.get("isbn") or data.get("isbn_13") or data.get("isbn13")
        if isbn:
            return FormatDetector._clean_isbn(str(isbn))
        
        # Generic формат
        isbn = data.get("isbn") or data.get("isbn13") or data.get("isbn_13")
        if isbn:
            return FormatDetector._clean_isbn(str(isbn))
        
        # ONIX формат
        for pi in data.get("product_identifier", []):
            if pi.get("type") in ("15", "02"):  # ISBN-13 or ISBN-10
                return FormatDetector._clean_isbn(pi.get("value", ""))
        
        return None
    
    @staticmethod
    def _clean_isbn(isbn: str) -> Optional[str]:
        """Очищає ISBN від дефісів та пробілів."""
        if not isbn:
            return None
        
        cleaned = re.sub(r'[-\s]', '', str(isbn)).strip()
        
        # Конвертація ISBN-10 в ISBN-13
        if len(cleaned) == 10 and cleaned.isdigit():
            # Додаємо префікс 978 та перераховуємо контрольну цифру
            isbn13 = "978" + cleaned[:-1]
            check_digit = FormatDetector._calculate_isbn13_check(isbn13)
            return isbn13 + str(check_digit)
        
        if len(cleaned) == 13 and cleaned.isdigit():
            return cleaned
        
        return cleaned if cleaned else None
    
    @staticmethod
    def _calculate_isbn13_check(isbn12: str) -> int:
        """Обчислює контрольну цифру для ISBN-13."""
        if len(isbn12) != 12:
            return 0
        
        total = 0
        for i, digit in enumerate(isbn12):
            multiplier = 1 if i % 2 == 0 else 3
            total += int(digit) * multiplier
        
        remainder = total % 10
        return 0 if remainder == 0 else 10 - remainder
    
    @staticmethod
    def extract_title(data: Dict[str, Any]) -> Optional[str]:
        """Витягує назву з даних різних форматів."""
        # Yakaboo
        title = data.get("name") or data.get("h1")
        if title:
            return str(title).strip()
        
        # Vivat / Generic
        title = data.get("title") or data.get("name")
        if title:
            return str(title).strip()
        
        # ONIX
        for title_obj in data.get("titles", []):
            if title_obj.get("type") == "01":  # Distinctive title
                return title_obj.get("text", "").strip()
        
        return None


