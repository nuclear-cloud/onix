# app/schemas/product_market.py
"""
DTO для швидкого оновлення маркет-даних (ціни, наявність).
Використовується в Шляху 2 (Hourly Market Sync).
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class ProductMarketDTO(BaseModel):
    """
    Маленький папірець: тільки те, що часто змінюється.
    
    Це використовується для погодинного оновлення цін без
    перезавантаження всієї інформації про книгу.
    """
    # --- Ідентифікація ---
    isbn13: str = Field(..., description="ISBN-13 (для пошуку в базі)")
    sku: Optional[str] = Field(None, description="SKU для логів")
    
    # --- Маркет дані (що часто змінюються) ---
    price: Optional[float] = Field(None, description="Поточна ціна")
    old_price: Optional[float] = Field(None, description="Стара ціна")
    currency: str = Field(default="UAH", description="Валюта")
    in_stock: bool = Field(default=False, description="Наявність")
    url: Optional[str] = Field(None, description="URL продукту")
    
    # --- Метадані ---
    source: str = Field(..., description="Джерело (yakaboo, ksd)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "isbn13": "978-0441172719",
                "sku": "BOOK-999",
                "price": 650.0,
                "old_price": 750.0,
                "currency": "UAH",
                "in_stock": True,
                "url": "https://yakaboo.ua/ua/BOOK-999.html",
                "source": "yakaboo"
            }
        }
    
    @validator('isbn13')
    def validate_isbn13(cls, v):
        """Валідація ISBN-13."""
        if not v:
            raise ValueError('ISBN-13 is required')
        clean = v.replace('-', '').replace(' ', '')
        if len(clean) != 13 or not clean.isdigit():
            raise ValueError(f'Invalid ISBN-13: {v}')
        return clean
    
    @validator('price', 'old_price')
    def validate_price(cls, v):
        """Валідація цін."""
        if v is not None and v < 0:
            raise ValueError('Price cannot be negative')
        return v


class ProductPriceUpdateDTO(BaseModel):
    """
    DTO для оновлення тільки ціни (ще простіший варіант).
    """
    isbn13: str
    price: float
    currency: str = "UAH"
    source: str
    
    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Price cannot be negative')
        return v


class MarketUpdateResult(BaseModel):
    """
    Результат оновлення маркет-даних.
    """
    total: int = Field(..., description="Всього оброблено")
    updated: int = Field(..., description="Оновлено")
    created: int = Field(..., description="Створено нових")
    errors: int = Field(..., description="Помилок")
    skipped: int = Field(..., description="Пропущено")
    duration_seconds: float = Field(..., description="Час виконання")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 1000,
                "updated": 950,
                "created": 30,
                "errors": 5,
                "skipped": 15,
                "duration_seconds": 45.2
            }
        }
