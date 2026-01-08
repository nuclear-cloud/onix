"""
Transformer Registry

Реєстр трансформерів для різних форматів даних.
"""
from typing import Dict, Any, Callable, Optional
from app.scraper.yakaboo import yakaboo_to_onix
from app.processors.format_detector import FormatDetector


class TransformerRegistry:
    """Реєстр трансформерів для різних форматів."""
    
    _transformers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
    
    @classmethod
    def register(cls, format_name: str, transformer: Callable):
        """Реєструє трансформер для формату."""
        cls._transformers[format_name] = transformer
    
    @classmethod
    def get_transformer(cls, format_name: str) -> Optional[Callable]:
        """Отримує трансформер для формату."""
        return cls._transformers.get(format_name)
    
    @classmethod
    def transform(cls, data: Dict[str, Any], format_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Трансформує дані в ONIX формат.
        
        Args:
            data: Вхідні дані
            format_name: Назва формату (якщо None - визначається автоматично)
        
        Returns:
            ONIX структура
        """
        # Якщо формат не вказано - визначаємо автоматично
        if format_name is None:
            format_name = FormatDetector.detect_format(data)
        
        # Якщо дані вже в ONIX форматі - повертаємо як є
        if format_name == "onix":
            return data
        
        # Отримуємо трансформер
        transformer = cls.get_transformer(format_name)
        
        if transformer is None:
            raise ValueError(
                f"Трансформер для формату '{format_name}' не знайдено. "
                f"Доступні формати: {list(cls._transformers.keys())}"
            )
        
        return transformer(data)
    
    @classmethod
    def list_formats(cls) -> list:
        """Повертає список підтримуваних форматів."""
        return list(cls._transformers.keys())


# Реєстрація трансформерів
TransformerRegistry.register("yakaboo", yakaboo_to_onix)

# TODO: Додати інші трансформери
# TransformerRegistry.register("vivat", vivat_to_onix)
# TransformerRegistry.register("generic", generic_to_onix)


