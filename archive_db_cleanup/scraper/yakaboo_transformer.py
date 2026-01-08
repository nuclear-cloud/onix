"""
Yakaboo to ONIX Transformer (Legacy Compatibility Layer)

⚠️ DEPRECATED: Використовуйте app.scraper.yakaboo замість цього модуля.

Цей файл залишено для зворотної сумісності.
Всі функції автоматично імпортуються з нового модуля app.scraper.yakaboo.
"""

# Імпортуємо все з нового модуля для зворотної сумісності
from app.scraper.yakaboo import (
    yakaboo_to_onix,
    BINDING_TO_ONIX,
    LANG_TO_ONIX,
    PUBLICATION_TYPE_TO_ONIX,
    ILLUSTRATION_TYPE_TO_ONIX,
    AGE_TO_ONIX,
)

# Імпортуємо helper функції
from app.scraper.yakaboo.helpers import (
    safe_get,
    to_list,
    extract_label_value,
    parse_dimensions,
)

# Імпортуємо парсери
from app.scraper.yakaboo.extractor import (
    parse_contributors,
    parse_text_content,
    parse_prices,
    parse_supporting_resources,
    parse_supply,
    parse_subjects_extended,
    parse_measures_extended,
    parse_audience_extended,
    parse_publishing_dates,
)

# Експортуємо все для зворотної сумісності
__all__ = [
    "yakaboo_to_onix",
    "BINDING_TO_ONIX",
    "BINDING_TYPE_TO_ONIX",  # Аліас для зворотної сумісності
    "LANG_TO_ONIX",
    "PUBLICATION_TYPE_TO_ONIX",
    "ILLUSTRATION_TYPE_TO_ONIX",
    "AGE_TO_ONIX",
    "safe_get",
    "to_list",
    "extract_label_value",
    "parse_dimensions",
    "parse_contributors",
    "parse_text_content",
    "parse_prices",
    "parse_supporting_resources",
    "parse_supply",
    "parse_subjects_extended",
    "parse_measures_extended",
    "parse_audience_extended",
    "parse_publishing_dates",
]

# Аліас для зворотної сумісності
BINDING_TYPE_TO_ONIX = BINDING_TO_ONIX
