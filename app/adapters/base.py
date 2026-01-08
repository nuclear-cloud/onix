# app/adapters/base.py
"""
Базовий адаптер для всіх джерел даних.
Визначає загальні правила та інтерфейс.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class BaseAdapter(ABC):
    """
    Базовий клас для всіх адаптерів (Yakaboo, KSD, Vivat, etc.)
    
    Кожен адаптер повинен вміти:
    1. Парсити сирий JSON у стандартну структуру
    2. Валідувати дані
    3. Повертати як повний, так і швидкий формат
    """
    
    def __init__(self, source_name: str):
        """
        Args:
            source_name: Назва джерела (yakaboo, ksd, vivat)
        """
        self.source_name = source_name
        self.stats = {
            "processed": 0,
            "errors": 0,
            "warnings": 0
        }
    
    @abstractmethod
    def parse_full(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Повне розпакування: всі поля, описи, зображення.
        
        Args:
            raw_data: Сирі дані від джерела
            
        Returns:
            Повна структура для бази даних
        """
        pass
    
    @abstractmethod
    def parse_market(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Швидке розпакування: тільки ціни та наявність.
        
        Args:
            raw_data: Сирі дані від джерела
            
        Returns:
            Маленька структура (тільки критичні поля)
        """
        pass
    
    @abstractmethod
    def extract_isbn13(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """
        Швидко дістає ISBN-13 без повного парсингу.
        
        Args:
            raw_data: Сирі дані
            
        Returns:
            ISBN-13 або None
        """
        pass
    
    @abstractmethod
    def validate(self, raw_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Перевіряє чи дані валідні.
        
        Args:
            raw_data: Сирі дані
            
        Returns:
            (is_valid, list_of_errors)
        """
        pass
    
    def get_stats(self) -> Dict[str, int]:
        """Повертає статистику обробки."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Скидає статистику."""
        self.stats = {"processed": 0, "errors": 0, "warnings": 0}
    
    def log_error(self, message: str):
        """Логує помилку."""
        self.stats["errors"] += 1
        print(f"❌ [{self.source_name}] {message}")
    
    def log_warning(self, message: str):
        """Логує попередження."""
        self.stats["warnings"] += 1
        print(f"⚠️  [{self.source_name}] {message}")
    
    def log_success(self, message: str):
        """Логує успіх."""
        self.stats["processed"] += 1
        print(f"✅ [{self.source_name}] {message}")
