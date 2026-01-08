"""
Catalog API Router - Prisma ORM version.

Endpoints: /products, /products/{id}, /search
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from prisma import Prisma
from app.core.prisma_db import get_db
from app.services.prisma_catalog_service import PrismaCatalogService

router = APIRouter(
    prefix="/catalog",
    tags=["catalog"],
)


@router.get(
    "/products",
    summary="List products",
    description="Get paginated list of books.",
)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    ukrainian_only: bool = Query(False, description="Filter Ukrainian books only"),
    db: Prisma = Depends(get_db),
) -> dict:
    """
    List active products with pagination.
    
    **Parameters:**
    - `page`: Page number (min. 1)
    - `limit`: Items per page (1-100, default 20)
    - `ukrainian_only`: Filter for Ukrainian books only
    """
    offset = (page - 1) * limit
    service = PrismaCatalogService(db)
    return await service.get_catalog(
        limit=limit,
        offset=offset,
        ukrainian_only=ukrainian_only
    )


@router.get(
    "/products/{isbn13}",
    summary="Get product details",
    description="Get full details of a book by ISBN-13.",
)
async def get_product(
    isbn13: str,
    db: Prisma = Depends(get_db),
) -> dict:
    """Get full product details by ISBN-13."""
    service = PrismaCatalogService(db)
    product = await service.get_book_details(isbn13)
    
    if not product:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return product


@router.get(
    "/search",
    summary="Search books",
    description="Full-text search across titles.",
)
async def search_books(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Prisma = Depends(get_db),
) -> dict:
    """Search for books by title."""
    service = PrismaCatalogService(db)
    return await service.search_books(query=q, limit=limit, offset=offset)


@router.get(
    "/recent",
    summary="Recent additions",
    description="Get recently added books.",
)
async def recent_books(
    limit: int = Query(20, ge=1, le=50),
    db: Prisma = Depends(get_db),
) -> dict:
    """Get recently added books."""
    service = PrismaCatalogService(db)
    items = await service.get_recent_additions(limit=limit)
    return {
        'count': len(items),
        'items': items,
    }


@router.get(
    "/publisher/{publisher_id}",
    summary="Books by publisher",
    description="Get all books from a specific publisher.",
)
async def books_by_publisher(
    publisher_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Prisma = Depends(get_db),
) -> dict:
    """Get books by publisher."""
    offset = (page - 1) * limit
    service = PrismaCatalogService(db)
    return await service.get_by_publisher(
        publisher_id=publisher_id,
        limit=limit,
        offset=offset
    )


@router.get(
    "/stats",
    summary="Catalog statistics",
    description="Get catalog statistics and metrics.",
)
async def catalog_stats(
    db: Prisma = Depends(get_db),
) -> dict:
    """Get catalog statistics."""
    service = PrismaCatalogService(db)
    return await service.get_statistics()
