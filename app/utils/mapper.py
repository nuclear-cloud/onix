# utils/mapper.py
"""
Універсальний мапер для трансформації JSON структур.
Містить утиліти для роботи з глибокими структурами та атрибутами.
"""
from typing import Dict, Any, List, Optional, Callable
from app.config.thema_map import CATEGORY_TO_THEMA, get_default_thema


def get_deep_value(data: Dict, path: str) -> Any:
    """
    Дістає значення з глибини JSON по шляху 'field.subfield.0.value'.
    
    Args:
        data: Словник з даними
        path: Шлях до значення через крапку
        
    Returns:
        Значення або None якщо не знайдено
        
    Example:
        >>> data = {"price_info": {"final_price": 100}}
        >>> get_deep_value(data, "price_info.final_price")
        100
    """
    if not data or not path:
        return None
    
    keys = path.split('.')
    value = data
    
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        elif isinstance(value, list) and key.isdigit():
            try:
                value = value[int(key)]
            except (IndexError, ValueError):
                return None
        else:
            return None
            
        if value is None:
            return None
            
    return value


def find_attribute(attributes: List[Dict], target_code: str) -> Any:
    """
    Шукає значення в списку атрибутів (Magento/EAV style).
    
    Args:
        attributes: Список словників з атрибутами
        target_code: Код атрибута для пошуку
        
    Returns:
        Значення атрибута або None
        
    Example:
        >>> attrs = [{"attribute_code": "isbn", "value": "978-123"}]
        >>> find_attribute(attrs, "isbn")
        "978-123"
    """
    if not attributes:
        return None
        
    for attr in attributes:
        if attr.get('attribute_code') == target_code:
            return attr.get('value')
            
    return None


def map_thema_subject(categories: List[Dict]) -> str:
    """
    Перетворює список категорій Yakaboo в код THEMA.
    
    Стратегія:
    1. Спочатку шукає в найглибшій категорії (остання в списку)
    2. Якщо не знайдено, проходить по всіх категоріях з кінця
    3. Повертає дефолтне значення якщо нічого не знайдено
    
    Args:
        categories: Список категорій від Yakaboo
        
    Returns:
        Код THEMA (наприклад "FBA" для фантастики)
    """
    if not categories:
        return get_default_thema()
    
    # Спроба 1: Беремо останню (найглибшу) категорію
    try:
        last_category = categories[-1].get('name')
        if last_category and last_category in CATEGORY_TO_THEMA:
            return CATEGORY_TO_THEMA[last_category]
    except (IndexError, AttributeError):
        pass

    # Спроба 2: Проходимо по всіх категоріях, йдемо з кінця
    for cat in reversed(categories):
        name = cat.get('name')
        if name and name in CATEGORY_TO_THEMA:
            return CATEGORY_TO_THEMA[name]
    
    # Якщо нічого не знайдено - логуємо та повертаємо дефолт
    category_names = [c.get('name') for c in categories if c.get('name')]
    if category_names:
        print(f"⚠️  Unknown Category: {category_names}")
    
    return get_default_thema()


def extract_first_image(media_gallery: List[Dict]) -> Optional[str]:
    """
    Витягує перше зображення з media gallery.
    
    Args:
        media_gallery: Список медіа об'єктів
        
    Returns:
        URL або шлях до зображення
    """
    if not media_gallery or not isinstance(media_gallery, list):
        return None
        
    try:
        return media_gallery[0].get('file')
    except (IndexError, AttributeError):
        return None


def apply_mapping(source: Dict, config: Dict[str, Any]) -> Dict:
    """
    Головна функція запуску мапінгу.
    
    Підтримує:
    - Прості шляхи (string): "field.subfield"
    - Функції (callable): lambda src: ...
    - Константи: будь-яке інше значення
    
    Args:
        source: Вхідні дані (raw JSON)
        config: Конфігурація мапінгу
        
    Returns:
        Трансформовані дані
        
    Example:
        >>> config = {"name": "title", "active": lambda s: s.get("status") == 1}
        >>> apply_mapping({"title": "Book", "status": 1}, config)
        {"name": "Book", "active": True}
    """
    result = {}
    
    for target_field, rule in config.items():
        try:
            if isinstance(rule, str):
                # Простий шлях до поля
                result[target_field] = get_deep_value(source, rule)
            elif callable(rule):
                # Кастомна функція
                result[target_field] = rule(source)
            else:
                # Константа
                result[target_field] = rule
                
        except Exception as e:
            print(f"❌ Error mapping field '{target_field}': {e}")
            result[target_field] = None
            
    return result


def safe_int(value: Any) -> Optional[int]:
    """Безпечне перетворення в int."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_float(value: Any) -> Optional[float]:
    """Безпечне перетворення в float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_bool(value: Any) -> bool:
    """Безпечне перетворення в bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'y', 'active')
    return bool(value)
