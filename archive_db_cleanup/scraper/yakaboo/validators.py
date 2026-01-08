"""
ONIX Structure Validators

Функції для валідації ONIX структури після трансформації.
"""

from typing import Dict, Any, List, Tuple


def validate_onix_structure(onix_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Валідує ONIX структуру.
    
    Перевіряє:
    - Наявність обов'язкових полів
    - Правильність типів даних
    - Валідність значень
    
    Args:
        onix_data: ONIX структура для валідації
        
    Returns:
        Tuple[is_valid, list_of_errors]
        
    Example:
        >>> onix = {"record_reference": "yakaboo_123", "titles": []}
        >>> is_valid, errors = validate_onix_structure(onix)
        >>> print(is_valid, errors)
        False ['Відсутнє поле "titles" або воно порожнє']
    """
    errors = []
    
    # Перевірка обов'язкових полів
    if "record_reference" not in onix_data or not onix_data["record_reference"]:
        errors.append('Відсутнє поле "record_reference"')
    
    if "notification_type" not in onix_data:
        errors.append('Відсутнє поле "notification_type"')
    
    # Перевірка titles
    if "titles" not in onix_data:
        errors.append('Відсутнє поле "titles"')
    elif not isinstance(onix_data["titles"], list):
        errors.append('"titles" має бути списком')
    elif len(onix_data["titles"]) == 0:
        errors.append('Відсутнє поле "titles" або воно порожнє')
    
    # Перевірка product_identifier
    if "product_identifier" in onix_data:
        if not isinstance(onix_data["product_identifier"], list):
            errors.append('"product_identifier" має бути списком')
        else:
            # Перевірка що є хоча б один ідентифікатор
            if len(onix_data["product_identifier"]) == 0:
                errors.append('"product_identifier" не може бути порожнім')
    
    # Перевірка contributors
    if "contributors" in onix_data:
        if not isinstance(onix_data["contributors"], list):
            errors.append('"contributors" має бути списком')
        else:
            # Перевірка структури contributors
            for i, contrib in enumerate(onix_data["contributors"]):
                if not isinstance(contrib, dict):
                    errors.append(f'"contributors[{i}]" має бути словником')
                elif "role" not in contrib:
                    errors.append(f'"contributors[{i}]" має містити поле "role"')
                elif "name" not in contrib:
                    errors.append(f'"contributors[{i}]" має містити поле "name"')
    
    # Перевірка languages
    if "languages" in onix_data:
        if not isinstance(onix_data["languages"], list):
            errors.append('"languages" має бути списком')
        else:
            for i, lang in enumerate(onix_data["languages"]):
                if not isinstance(lang, dict):
                    errors.append(f'"languages[{i}]" має бути словником')
                elif "code" not in lang:
                    errors.append(f'"languages[{i}]" має містити поле "code"')
    
    # Перевірка publishers
    if "publishers" in onix_data:
        if not isinstance(onix_data["publishers"], list):
            errors.append('"publishers" має бути списком')
        else:
            for i, pub in enumerate(onix_data["publishers"]):
                if not isinstance(pub, dict):
                    errors.append(f'"publishers[{i}]" має бути словником')
                elif "name" not in pub:
                    errors.append(f'"publishers[{i}]" має містити поле "name"')
    
    # Перевірка prices
    if "prices" in onix_data:
        if not isinstance(onix_data["prices"], list):
            errors.append('"prices" має бути списком')
        else:
            for i, price in enumerate(onix_data["prices"]):
                if not isinstance(price, dict):
                    errors.append(f'"prices[{i}]" має бути словником')
                elif "type" not in price:
                    errors.append(f'"prices[{i}]" має містити поле "type"')
                elif "amount" not in price:
                    errors.append(f'"prices[{i}]" має містити поле "amount"')
    
    # Перевірка supply_detail
    if "supply_detail" in onix_data:
        if not isinstance(onix_data["supply_detail"], dict):
            errors.append('"supply_detail" має бути словником')
        elif "availability" not in onix_data["supply_detail"]:
            errors.append('"supply_detail" має містити поле "availability"')
    
    return len(errors) == 0, errors


def validate_onix_basic(onix_data: Dict[str, Any]) -> bool:
    """
    Базова валідація ONIX структури (швидка перевірка).
    
    Args:
        onix_data: ONIX структура
        
    Returns:
        True якщо структура валідна, False інакше
    """
    if not isinstance(onix_data, dict):
        return False
    
    # Мінімальні вимоги
    if "record_reference" not in onix_data:
        return False
    
    if "titles" not in onix_data or not isinstance(onix_data["titles"], list):
        return False
    
    if len(onix_data["titles"]) == 0:
        return False
    
    return True





ONIX Structure Validators

Функції для валідації ONIX структури після трансформації.
"""

from typing import Dict, Any, List, Tuple


def validate_onix_structure(onix_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Валідує ONIX структуру.
    
    Перевіряє:
    - Наявність обов'язкових полів
    - Правильність типів даних
    - Валідність значень
    
    Args:
        onix_data: ONIX структура для валідації
        
    Returns:
        Tuple[is_valid, list_of_errors]
        
    Example:
        >>> onix = {"record_reference": "yakaboo_123", "titles": []}
        >>> is_valid, errors = validate_onix_structure(onix)
        >>> print(is_valid, errors)
        False ['Відсутнє поле "titles" або воно порожнє']
    """
    errors = []
    
    # Перевірка обов'язкових полів
    if "record_reference" not in onix_data or not onix_data["record_reference"]:
        errors.append('Відсутнє поле "record_reference"')
    
    if "notification_type" not in onix_data:
        errors.append('Відсутнє поле "notification_type"')
    
    # Перевірка titles
    if "titles" not in onix_data:
        errors.append('Відсутнє поле "titles"')
    elif not isinstance(onix_data["titles"], list):
        errors.append('"titles" має бути списком')
    elif len(onix_data["titles"]) == 0:
        errors.append('Відсутнє поле "titles" або воно порожнє')
    
    # Перевірка product_identifier
    if "product_identifier" in onix_data:
        if not isinstance(onix_data["product_identifier"], list):
            errors.append('"product_identifier" має бути списком')
        else:
            # Перевірка що є хоча б один ідентифікатор
            if len(onix_data["product_identifier"]) == 0:
                errors.append('"product_identifier" не може бути порожнім')
    
    # Перевірка contributors
    if "contributors" in onix_data:
        if not isinstance(onix_data["contributors"], list):
            errors.append('"contributors" має бути списком')
        else:
            # Перевірка структури contributors
            for i, contrib in enumerate(onix_data["contributors"]):
                if not isinstance(contrib, dict):
                    errors.append(f'"contributors[{i}]" має бути словником')
                elif "role" not in contrib:
                    errors.append(f'"contributors[{i}]" має містити поле "role"')
                elif "name" not in contrib:
                    errors.append(f'"contributors[{i}]" має містити поле "name"')
    
    # Перевірка languages
    if "languages" in onix_data:
        if not isinstance(onix_data["languages"], list):
            errors.append('"languages" має бути списком')
        else:
            for i, lang in enumerate(onix_data["languages"]):
                if not isinstance(lang, dict):
                    errors.append(f'"languages[{i}]" має бути словником')
                elif "code" not in lang:
                    errors.append(f'"languages[{i}]" має містити поле "code"')
    
    # Перевірка publishers
    if "publishers" in onix_data:
        if not isinstance(onix_data["publishers"], list):
            errors.append('"publishers" має бути списком')
        else:
            for i, pub in enumerate(onix_data["publishers"]):
                if not isinstance(pub, dict):
                    errors.append(f'"publishers[{i}]" має бути словником')
                elif "name" not in pub:
                    errors.append(f'"publishers[{i}]" має містити поле "name"')
    
    # Перевірка prices
    if "prices" in onix_data:
        if not isinstance(onix_data["prices"], list):
            errors.append('"prices" має бути списком')
        else:
            for i, price in enumerate(onix_data["prices"]):
                if not isinstance(price, dict):
                    errors.append(f'"prices[{i}]" має бути словником')
                elif "type" not in price:
                    errors.append(f'"prices[{i}]" має містити поле "type"')
                elif "amount" not in price:
                    errors.append(f'"prices[{i}]" має містити поле "amount"')
    
    # Перевірка supply_detail
    if "supply_detail" in onix_data:
        if not isinstance(onix_data["supply_detail"], dict):
            errors.append('"supply_detail" має бути словником')
        elif "availability" not in onix_data["supply_detail"]:
            errors.append('"supply_detail" має містити поле "availability"')
    
    return len(errors) == 0, errors


def validate_onix_basic(onix_data: Dict[str, Any]) -> bool:
    """
    Базова валідація ONIX структури (швидка перевірка).
    
    Args:
        onix_data: ONIX структура
        
    Returns:
        True якщо структура валідна, False інакше
    """
    if not isinstance(onix_data, dict):
        return False
    
    # Мінімальні вимоги
    if "record_reference" not in onix_data:
        return False
    
    if "titles" not in onix_data or not isinstance(onix_data["titles"], list):
        return False
    
    if len(onix_data["titles"]) == 0:
        return False
    
    return True






