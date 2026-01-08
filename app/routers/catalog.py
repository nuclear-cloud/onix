"""
API Router - FastAPI endpoints для каталогу.

Маршрути: /products, /products/{id}, /search
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.services.catalog_service import CatalogService
from app.schemas import (
    ProductCardDTO,
    ProductDetailDTO,
    CatalogSearchResponseDTO,
    ErrorDTO,
)

router = APIRouter(
    prefix="/catalog",
    tags=["catalog"],
    responses={404: {"model": ErrorDTO}},
)


@router.get(
    "/products",
    response_model=CatalogSearchResponseDTO,
    summary="Список товарів",
    description="Отримати список активних товарів зі сторінкуванням.",
)
async def list_products(
    page: int = Query(1, ge=1, description="Номер сторінки"),
    limit: int = Query(20, ge=1, le=100, description="Товарів на сторінку"),
    session: AsyncSession = Depends(get_session),
) -> CatalogSearchResponseDTO:
    """
    Список активних товарів з сторінкуванням.
    
    **Параметри:**
    - `page`: Номер сторінки (мін. 1)
    - `limit`: Товарів на сторінку (1-100, за замовч. 20)
    """
    service = CatalogService(session)
    return await service.get_products_list(page=page, limit=limit)


@router.get(
    "/products/{product_id}",
    response_model=ProductDetailDTO,
    summary="Деталь товара",
    description="Отримати повну інформацію про товар.",
)
async def get_product_detail(
    product_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProductDetailDTO:
    """
    Детальна інформація про товар.
    
    **Параметри:**
    - `product_id`: UUID товара
    """
    service = CatalogService(session)
    product = await service.get_product_detail(product_id)
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Товар {product_id} не знайдено",
        )
    
    return product


@router.get(
    "/search",
    response_model=CatalogSearchResponseDTO,
    summary="Пошук товарів",
    description="Пошук з фільтром по тексту, THEMA коду та форматі.",
)
async def search_products(
    q: str = Query(None, min_length=1, description="Текст для пошуку"),
    thema: str = Query(None, min_length=1, description="THEMA код (Y, YF, YFB)"),
    format: str = Query(None, min_length=2, max_length=2, description="ONIX формат (BB, BC, EA)"),
    page: int = Query(1, ge=1, description="Номер сторінки"),
    limit: int = Query(20, ge=1, le=100, description="На сторінку"),
    session: AsyncSession = Depends(get_session),
) -> CatalogSearchResponseDTO:
    """
    Пошук товарів з фільтрами.
    
    **Параметри:**
    - `q`: Текст для пошуку (назва, автор)
    - `thema`: THEMA код (напр. "Y", "YF", "YFB")
    - `format`: ONIX формат (напр. "BB", "BC", "EA")
    - `page`: Сторінка
    - `limit`: На сторінку
    
    **Приклади:**
    - `/search?q=Гришем` - пошук за автором
    - `/search?thema=YFB` - фільтр по темі
    - `/search?format=BB&page=2` - формат зі сторінкуванням
    - `/search?q=Квітник&thema=Y&format=BC` - комбінований пошук
    """
    service = CatalogService(session)
    
    return await service.search(
        query=q,
        thema_code=thema,
        product_form=format,
        page=page,
        limit=limit,
    )
