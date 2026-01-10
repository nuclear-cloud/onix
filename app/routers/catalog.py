"""
Catalog API Router - Prisma-only (direct Prisma client queries).

Endpoints: /products, /products/{isbn13}, /search, /recent, /publisher/{publisher_name}, /stats, /health
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from prisma import Prisma
from app.core.prisma_db import get_db
from app.core.config import settings

router = APIRouter(prefix="/catalog", tags=["catalog"])

# ===== Stats Cache =====
_stats_cache: dict = {"data": None, "expires": None} 


@router.get(
    "/products",
    summary="List products",
    description="Get paginated list of books.",
)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    ukrainian_only: bool = Query(False, description="Filter Ukrainian books only (language_code='ukr')"),
    db: Prisma = Depends(get_db),
) -> dict:
    """List products with pagination using Prisma directly."""
    offset = (page - 1) * limit
    where = {"deleted_at": None}
    if ukrainian_only:
        where.update({"language_code": "ukr"})

    total = await db.catalogproduct.count(where=where)
    products = await db.catalogproduct.find_many(
        skip=offset,
        take=limit,
        where=where,
        order={"created_at": "desc"},
        include={
            "contributors": True,
            "subjects": True,
            "text_content": True,
            "media_files": True,
        },
    )

    def to_card(p) -> dict:
        return {
            "id": int(p.id),
            "isbn13": p.isbn13,
            "title": p.title,
            "subtitle": p.subtitle,
            "publisher_name": p.publisher_name,
            "publication_date": p.publication_date,
            "product_form_code": p.product_form_code,
            "language_code": p.language_code,
        }

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [to_card(p) for p in products],
    }


@router.get(
    "/products/{isbn13}",
    summary="Get product details",
    description="Get full details of a book by ISBN-13.",
)
async def get_product(
    isbn13: str,
    db: Prisma = Depends(get_db),
) -> dict:
    """Get full product details by ISBN-13 using Prisma."""
    product = await db.catalogproduct.find_unique(
        where={"isbn13": isbn13},
        include={
            "contributors": True,
            "subjects": True,
            "text_content": True,
            "media_files": True,
            "prices": True,
            "sales_rights": True,
            "related_products_from": True,
            "related_products_to": True,
        },
    )

    if not product:
        raise HTTPException(status_code=404, detail="Book not found")

    def map_product(p) -> dict:
        return {
            "id": int(p.id),
            "isbn13": p.isbn13,
            "isbn10": p.isbn10,
            "title": p.title,
            "subtitle": p.subtitle,
            "publisher_name": p.publisher_name,
            "publication_date": p.publication_date,
            "product_form_code": p.product_form_code,
            "language_code": p.language_code,
            "page_count": p.page_count,
            "subjects": [
                {"scheme": s.scheme_code, "code": s.subject_code, "text": s.subject_heading_text}
                for s in (p.subjects or [])
            ],
            "contributors": [
                {
                    "role": c.role_code,
                    "type": c.contributor_type,
                    "name": c.person_name or c.corporate_name,
                    "sequence": c.sequence_number,
                }
                for c in (p.contributors or [])
            ],
            "descriptions": [
                {"type": t.text_type_code, "content": t.content}
                for t in (p.text_content or [])
            ],
            "media": [
                {"type": m.resource_content_type_code, "link": m.file_link}
                for m in (p.media_files or [])
            ],
        }

    return map_product(product)


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
    """Search books by title or subtitle."""
    items = await db.catalogproduct.find_many(
        where={
            "deleted_at": None,
            "OR": [
                {"title": {"contains": q, "mode": "insensitive"}},
                {"subtitle": {"contains": q, "mode": "insensitive"}},
            ],
        },
        take=limit,
        skip=offset,
        order={"created_at": "desc"},
    )
    return {"query": q, "count": len(items), "items": items}


@router.get(
    "/recent",
    summary="Recent additions",
    description="Get recently added books.",
)
async def recent_books(
    limit: int = Query(20, ge=1, le=50),
    db: Prisma = Depends(get_db),
) -> dict:
    items = await db.catalogproduct.find_many(
        take=limit,
        order={"created_at": "desc"},
        where={"deleted_at": None},
    )
    return {"count": len(items), "items": items}


@router.get(
    "/publisher/{publisher_name}",
    summary="Books by publisher",
    description="Get books from a specific publisher name.",
)
async def books_by_publisher(
    publisher_name: str = Path(..., min_length=1, max_length=200, description="Publisher name"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Prisma = Depends(get_db),
) -> dict:
    offset = (page - 1) * limit
    where = {
        "publisher_name": {"equals": publisher_name, "mode": "insensitive"},
        "deleted_at": None,
    }
    total = await db.catalogproduct.count(where=where)
    items = await db.catalogproduct.find_many(
        where=where,
        skip=offset,
        take=limit,
        order={"created_at": "desc"},
    )
    return {"total": total, "page": page, "limit": limit, "items": items}


@router.get(
    "/stats",
    summary="Catalog statistics",
    description="Get catalog statistics and metrics. Cached for 5 minutes.",
)
async def catalog_stats(
    db: Prisma = Depends(get_db),
) -> dict:
    """Get catalog statistics with caching."""
    global _stats_cache
    now = datetime.now()
    
    # Return cached data if valid
    if _stats_cache["data"] and _stats_cache["expires"] and _stats_cache["expires"] > now:
        return {**_stats_cache["data"], "cached": True}
    
    # Fresh query
    total = await db.catalogproduct.count()
    with_isbn = await db.catalogproduct.count(where={"isbn13": {"not": None}})
    with_publisher = await db.catalogproduct.count(where={"publisher_name": {"not": None}})
    ukr = await db.catalogproduct.count(where={"language_code": "ukr"})
    
    stats = {
        "total_books": total,
        "with_isbn": with_isbn,
        "with_publisher": with_publisher,
        "ukrainian_books": ukr,
        "coverage_isbn": f"{(with_isbn/total*100):.1f}%" if total else "0%",
        "cached": False,
    }
    
    # Cache for configured TTL
    _stats_cache["data"] = stats
    _stats_cache["expires"] = now + timedelta(seconds=settings.STATS_CACHE_TTL)
    
    return stats


@router.get(
    "/health",
    summary="Health check",
    description="Check API and database health.",
)
async def health_check(
    db: Prisma = Depends(get_db),
) -> dict:
    """Health check endpoint for monitoring."""
    try:
        # Quick DB check
        count = await db.catalogproduct.count(take=1)
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
