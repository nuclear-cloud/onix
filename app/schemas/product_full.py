# app/schemas/product_full.py
"""
DTO для повного опису продукту.
Використовується в Шляху 1 (Daily Catalog Import).
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProductFullDTO(BaseModel):
    """
    Великий контейнер: всі дані про книгу.
    
    Це те, що ми зберігаємо в базі після повного імпорту.
    """
    # --- Ідентифікація ---
    isbn13: str = Field(..., description="ISBN-13 (головний ключ)")
    external_id: Optional[int] = Field(None, description="ID у джерелі (Yakaboo entity_id)")
    sku: Optional[str] = Field(None, description="SKU у джерелі")
    
    # --- Основні дані ---
    name: str = Field(..., description="Назва книги")
    author: Optional[str] = Field(None, description="Автор")
    publisher: Optional[str] = Field(None, description="Видавництво")
    
    # --- Описи ---
    description: Optional[str] = Field(None, description="Повний опис")
    short_description: Optional[str] = Field(None, description="Короткий опис")
    
    # --- Ціни ---
    price: Optional[float] = Field(None, description="Поточна ціна")
    old_price: Optional[float] = Field(None, description="Стара ціна (зачеркнута)")
    currency: str = Field(default="UAH", description="Валюта")
    
    # --- Характеристики ---
    pages: Optional[int] = Field(None, description="Кількість сторінок")
    year: Optional[int] = Field(None, description="Рік видання")
    language: Optional[str] = Field(None, description="Мова (ukr, eng, rus)")
    binding: Optional[str] = Field(None, description="Тип обкладинки (тверда, м'яка)")
    weight: Optional[float] = Field(None, description="Вага в грамах")
    dimensions: Optional[str] = Field(None, description="Розміри (формат)")
    
    # --- Медіа ---
    main_image: Optional[str] = Field(None, description="URL головного зображення")
    images: List[str] = Field(default_factory=list, description="Всі зображення")
    
    # --- Класифікація ---
    thema_subject: Optional[str] = Field(None, description="Код THEMA")
    categories: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Категорії джерела"
    )
    
    # --- Метадані ---
    source: str = Field(..., description="Джерело (yakaboo, ksd)")
    url: Optional[str] = Field(None, description="URL продукту")
    in_stock: bool = Field(default=False, description="Наявність")
    is_active: bool = Field(default=True, description="Чи активний")
    
    # --- Дати ---
    created_at: Optional[datetime] = Field(None, description="Дата створення у джерелі")
    updated_at: Optional[datetime] = Field(None, description="Дата оновлення у джерелі")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "isbn13": "978-0441172719",
                "name": "Дюна",
                "author": "Френк Герберт",
                "publisher": "КСД",
                "price": 600.0,
                "old_price": 750.0,
                "currency": "UAH",
                "pages": 896,
                "year": 2019,
                "language": "ukr",
                "thema_subject": "FBA",
                "source": "yakaboo",
                "in_stock": True,
            }
        }
    )
    
    @field_validator('isbn13', mode='before')
    @classmethod
    def validate_isbn13(cls, v):
        """Валідація ISBN-13."""
        if not v:
            raise ValueError('ISBN-13 is required')
        # Прибираємо дефіси
        clean = v.replace('-', '').replace(' ', '')
        if len(clean) != 13 or not clean.isdigit():
            raise ValueError(f'Invalid ISBN-13: {v}')
        return clean
    
    @field_validator('price', 'old_price', mode='before')
    @classmethod
    def validate_price(cls, v):
        """Валідація цін."""
        if v is not None and v < 0:
            raise ValueError('Price cannot be negative')
        return v


class ProductCreateDTO(BaseModel):
    """
    DTO для створення нового продукту в базі.
    Мінімально необхідні поля.
    """
    isbn13: str
    name: str
    source: str
    price: Optional[float] = None
    
    @field_validator('isbn13', mode='before')
    @classmethod
    def validate_isbn13(cls, v):
        clean = v.replace('-', '').replace(' ', '')
        if len(clean) != 13 or not clean.isdigit():
            raise ValueError(f'Invalid ISBN-13: {v}')
        return clean
