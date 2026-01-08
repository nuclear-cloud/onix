"""
API DTOs (Data Transfer Objects) для каталогу і ціни.

Для REST API responses — відокремлено від БД моделей.
"""

from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# =====価格 (Price) =====

class PriceDTO(BaseModel):
    """Ціна продукту."""
    amount: Decimal = Field(..., description="Сума")
    currency: str = Field(default="UAH", description="Валюта (ISO 4217)")
    type: str = Field(default="RRP", description="Тип ціни (RRP/Net)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": "299.99",
                "currency": "UAH",
                "type": "RRP"
            }
        }


# ===== КАТАЛОГ =====

class ContributorDTO(BaseModel):
    """Автор/редактор/перекладач."""
    name: str
    role: str = Field(..., description="ONIX код ролі (A01/B06)")
    role_label: Optional[str] = Field(None, description="Лабель українською")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Марко Вовк",
                "role": "A01",
                "role_label": "Автор"
            }
        }


class TitleDTO(BaseModel):
    """Назва продукту."""
    title: str
    subtitle: Optional[str] = None
    type: str = Field(default="01", description="Тип назви")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Марко Вовк. Квітник",
                "subtitle": "Сучасна лірика",
                "type": "01"
            }
        }


class SubjectDTO(BaseModel):
    """Категорія/тема (THEMA)."""
    code: str = Field(..., description="THEMA код (Y, YF, YFB)")
    label: Optional[str] = Field(None, description="Назва категорії")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "YF",
                "label": "Художна фікція"
            }
        }


class ProductCardDTO(BaseModel):
    """Картка продукту (коротка версія для списку)."""
    id: UUID
    isbn: Optional[str]
    title: str
    format: str = Field(..., description="Формат (BB/BC/EA/AJ)")
    format_label: Optional[str] = Field(None, description="Твердопереплет/PDF/Аудіо")
    type: str = Field(..., description="physical|digital|audio")
    is_buyable: bool
    is_archived: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "isbn": "9786177902421",
                "title": "Марко Вовк. Квітник",
                "format": "BB",
                "format_label": "Твердопереплет",
                "type": "physical",
                "is_buyable": True,
                "is_archived": False
            }
        }


class ProductDetailDTO(BaseModel):
    """Повна деталь продукту (для сторінки товару)."""
    id: UUID
    isbn: Optional[str] = None
    ean: Optional[str] = None
    sku: Optional[str] = None
    
    # Основні
    title: TitleDTO
    description: Optional[str] = Field(None, description="Анотація")
    
    # Формат & Статус
    format: str = Field(..., description="BB/BC/EA")
    format_label: Optional[str] = None
    type: str = Field(..., description="physical|digital|audio")
    status: str = Field(..., description="04/02/07")
    status_label: Optional[str] = None
    is_buyable: bool
    is_archived: bool
    
    # Метадані
    languages: List[str] = Field(default_factory=list, description="['uk', 'en']")
    subjects: List[SubjectDTO] = Field(default_factory=list, description="THEMA коди")
    
    # Автори
    contributors: List[ContributorDTO] = Field(default_factory=list)
    
    # Розміри (для фізичних)
    pages: Optional[int] = None
    height_mm: Optional[int] = None
    width_mm: Optional[int] = None
    weight_g: Optional[int] = None
    
    # Дати
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Видавець
    publisher: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "isbn": "9786177902421",
                "title": {
                    "title": "Марко Вовк. Квітник",
                    "subtitle": "Сучасна лірика"
                },
                "format": "BB",
                "format_label": "Твердопереплет",
                "type": "physical",
                "status": "04",
                "status_label": "Активна",
                "is_buyable": True,
                "is_archived": False,
                "subjects": [
                    {"code": "DSU", "label": "Українська поезія"}
                ],
                "contributors": [
                    {
                        "name": "Марко Вовк",
                        "role": "A01",
                        "role_label": "Автор"
                    }
                ],
                "publisher": "VIVAT",
                "pages": 256
            }
        }


class PriceDetailDTO(BaseModel):
    """Детальна інформація про ціну."""
    product_id: UUID
    price: PriceDTO
    discount_percent: Optional[float] = Field(None, description="Знижка %")
    final_price: Optional[Decimal] = Field(None, description="Ціна після знижки")
    availability: str = Field(default="in_stock", description="in_stock|preorder|out_of_stock")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "550e8400-e29b-41d4-a716-446655440001",
                "price": {
                    "amount": "299.99",
                    "currency": "UAH",
                    "type": "RRP"
                },
                "discount_percent": 10.0,
                "final_price": "269.99",
                "availability": "in_stock"
            }
        }


class CatalogSearchRequestDTO(BaseModel):
    """Пошук в каталозі."""
    query: Optional[str] = Field(None, description="Текстовий пошук")
    thema_code: Optional[str] = Field(None, description="Фільтр по THEMA (Y/YF/YFB)")
    format: Optional[str] = Field(None, description="Фільтр по форматі (BB/BC/EA)")
    type: Optional[str] = Field(None, description="physical|digital|audio")
    is_available: Optional[bool] = Field(True, description="Тільки доступні")
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Марко Вовк",
                "thema_code": "DSU",
                "type": "physical",
                "page": 1,
                "limit": 20
            }
        }


class CatalogSearchResponseDTO(BaseModel):
    """Результати пошуку."""
    total: int
    page: int
    limit: int
    items: List[ProductCardDTO]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 150,
                "page": 1,
                "limit": 20,
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "isbn": "9786177902421",
                        "title": "Марко Вовк. Квітник",
                        "format": "BB",
                        "format_label": "Твердопереплет",
                        "type": "physical",
                        "is_buyable": True,
                        "is_archived": False
                    }
                ]
            }
        }


# ===== ERRORS =====

class ErrorDTO(BaseModel):
    """API помилка."""
    code: str
    message: str
    details: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "PRODUCT_NOT_FOUND",
                "message": "Товар не знайдено",
                "details": {"product_id": "550e8400-..."}
            }
        }
