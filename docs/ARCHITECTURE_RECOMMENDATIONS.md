# Architecture Recommendations - ONIX Aggregator

**Date:** 2025-01-15  
**Reviewer:** Code Cleanup Agent  
**Scope:** Security, Performance, Best Practices

---

## ✅ What's Working Well

1. **Clean 3-Tier Architecture** - Router → Service → Repository separation
2. **Prisma ORM** - Type-safe queries, proper includes for N:N relations
3. **Pydantic V2** - All schemas modernized to V2 patterns
4. **Structured Logging** - JSON-formatted structlog
5. **Rate Limiting** - slowapi with configurable limits
6. **Test Coverage** - 38 tests covering all layers

---

## 🔒 Security Recommendations

### HIGH Priority

#### 1. Environment Variable Validation
**Current:** Settings fallback to empty strings for DB URLs
```python
DATABASE_URL: str = os.getenv("DATABASE_URL", "")  # Could be empty
```

**Recommended:**
```python
from pydantic import SecretStr, field_validator

class Settings(BaseSettings):
    DATABASE_URL: SecretStr  # Required, no default
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db_url(cls, v):
        if not v or not v.get_secret_value().startswith("postgresql://"):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL")
        return v
```

#### 2. API Key Protection
**Current:** GROQ_API_KEY exposed as plain string
```python
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
```

**Recommended:**
```python
GROQ_API_KEY: SecretStr = ""  # Use SecretStr to prevent logging
```

#### 3. CORS Configuration
**Current:** Origins from env var with localhost defaults
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
```

**Recommended:** Add validation and production defaults:
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "")
if not ALLOWED_ORIGINS and os.getenv("ENVIRONMENT") == "production":
    raise ValueError("ALLOWED_ORIGINS must be set in production")
```

### MEDIUM Priority

#### 4. Input Sanitization
**Issue:** Publisher name parameter goes directly to query
```python
@router.get("/publisher/{publisher_name}")
async def books_by_publisher(publisher_name: str, ...):
    where = {"publisher_name": {"equals": publisher_name, ...}}
```

**Recommended:** Add length validation:
```python
from fastapi import Path

async def books_by_publisher(
    publisher_name: str = Path(..., min_length=1, max_length=200),
    ...
):
```

#### 5. Rate Limit by Endpoint
**Current:** Global rate limit
```python
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")
```

**Recommended:** Different limits per endpoint:
```python
@router.get("/search")
@limiter.limit("30/minute")  # Lower for expensive search
async def search_books(...):

@router.get("/stats")
@limiter.limit("10/minute")  # Lower for aggregate queries
async def catalog_stats(...):
```

---

## ⚡ Performance Recommendations

### HIGH Priority

#### 1. Add Database Indexes
**Current schema may lack indexes for common queries.**

Add to `prisma/schema.prisma`:
```prisma
model CatalogProduct {
  // ... existing fields
  
  @@index([publisher_name])
  @@index([language_code])
  @@index([created_at])
  @@index([title(type: GIN)])  // For full-text search
}
```

#### 2. Pagination Cursor-Based Option
**Current:** Offset pagination (slow for deep pages)
```python
products = await db.catalogproduct.find_many(skip=offset, take=limit)
```

**Recommended:** Add cursor option for large datasets:
```python
@router.get("/products")
async def list_products(
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100),
):
    if cursor:
        products = await db.catalogproduct.find_many(
            cursor={"id": int(cursor)},
            take=limit + 1,  # +1 to check if more exist
        )
    else:
        products = await db.catalogproduct.find_many(take=limit + 1)
    
    has_more = len(products) > limit
    if has_more:
        products = products[:-1]
    
    return {
        "items": products,
        "next_cursor": str(products[-1].id) if has_more else None,
    }
```

### MEDIUM Priority

#### 3. Response Model Validation
**Current:** Routes return raw dicts
```python
async def list_products(...) -> dict:
    return {"total": total, "items": items}
```

**Recommended:** Use response models for validation and OpenAPI:
```python
from app.schemas.catalog_dto import CatalogSearchResponseDTO

@router.get("/products", response_model=CatalogSearchResponseDTO)
async def list_products(...) -> CatalogSearchResponseDTO:
    ...
```

#### 4. Connection Pool Tuning
**Current:** Default Prisma connection pool

**Recommended:** Configure pool size in `prisma/schema.prisma`:
```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
  connectionLimit = 20  // Adjust based on load
}
```

#### 5. Caching for Stats Endpoint
**Current:** Stats queries run on every request
```python
@router.get("/stats")
async def catalog_stats(db):
    total = await db.catalogproduct.count()
    # ... multiple count queries
```

**Recommended:** Add caching:
```python
from functools import lru_cache
from datetime import datetime, timedelta
import asyncio

_stats_cache = {"data": None, "expires": None}

@router.get("/stats")
async def catalog_stats(db: Prisma = Depends(get_db)):
    now = datetime.now()
    if _stats_cache["data"] and _stats_cache["expires"] > now:
        return _stats_cache["data"]
    
    stats = {
        "total_books": await db.catalogproduct.count(),
        # ... other counts
    }
    
    _stats_cache["data"] = stats
    _stats_cache["expires"] = now + timedelta(minutes=5)
    return stats
```

---

## 🏗️ Architecture Improvements

### 1. Duplicate Route Definition
**Issue:** Two routes with same path pattern
```python
@router.get("/publisher/{publisher_name}")  # Line ~178
async def books_by_publisher(publisher_name: str, ...):

@router.get("/publisher/{publisher_id}")    # Line ~199
async def books_by_publisher(publisher_id: str, ...):  # Same function name!
```

**Fix:** Remove duplicate or rename to `/publisher/name/{name}` vs `/publisher/id/{id}`.

### 2. Service Layer Inconsistency
**Current:** Router sometimes uses service, sometimes direct Prisma
```python
# Direct Prisma (catalog.py:30)
products = await db.catalogproduct.find_many(...)

# Via Service (catalog.py:217)
service = PrismaCatalogService(db)
return await service.get_by_publisher(...)
```

**Recommended:** Choose one pattern consistently. For a project this size, direct Prisma in router is fine.

### 3. Error Response Standardization
**Current:** Different error formats
```python
raise HTTPException(status_code=404, detail="Book not found")
```

**Recommended:** Use ErrorDTO schema:
```python
from app.schemas.catalog_dto import ErrorDTO

@router.get("/products/{isbn13}")
async def get_product(...):
    if not product:
        raise HTTPException(
            status_code=404,
            detail=ErrorDTO(
                code="PRODUCT_NOT_FOUND",
                message="Товар не знайдено",
                details={"isbn13": isbn13}
            ).model_dump()
        )
```

---

## 📦 Dependency Cleanup

### Potentially Unused Packages in requirements.txt

| Package | Status | Recommendation |
|---------|--------|----------------|
| `beautifulsoup4` | No imports found | Remove if not used for scraping |
| `selectolax` | No imports found | Remove |
| `lxml` | No imports found | Remove |
| `instructor` | Only in docs | Remove if not using LLM |
| `typer` | Only in docs | Remove if no CLI commands |
| `rich` | Only in docs | Remove if not using |

**Audit command:**
```bash
pip install pipreqs
pipreqs /home/ubuntu/onix_project --force
# Compare generated requirements with current
```

---

## ✨ Quick Wins

1. **Add health endpoint** for monitoring:
```python
@router.get("/health")
async def health_check(db: Prisma = Depends(get_db)):
    try:
        await db.execute_raw("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )
```

2. **Add request ID middleware** for tracing:
```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

3. **Add API versioning** for future compatibility:
```python
router = APIRouter(prefix="/v1/catalog", tags=["catalog"])
```

---

## 📊 Summary

| Category | Issues Found | Priority Fixes |
|----------|-------------|----------------|
| Security | 5 | ENV validation, SecretStr, CORS |
| Performance | 5 | Indexes, cursor pagination, caching |
| Architecture | 3 | Duplicate route, service consistency |
| Dependencies | 6 | Unused packages to remove |

**Estimated effort:** 2-4 hours for high priority items.
