# API Implementation - Architecture Overview

**Date**: 2025-01-06  
**Status**: ✅ Complete (3-tier architecture implemented)

## Architecture Layers

### 1. Repository Layer (`app/repositories/product_repository.py`)

**Purpose**: Pure data access, zero business logic.

```python
# Methods
get_all(limit, offset) → (List[CatalogProduct], int)
get_by_id(product_id) → Optional[CatalogProduct]
get_by_isbn(isbn) → Optional[CatalogProduct]
search(query, thema_code, product_form, limit, offset) → (List[CatalogProduct], int)
get_onix_label(list_number, code) → Optional[str]
```

**Key Patterns**:
- AsyncSession dependency injection
- Parameterized queries (SQL injection safe)
- Returns ORM models directly (no DTOs)
- Handles complex joins (Title, Subject, Contributor)

---

### 2. Service Layer (`app/services/catalog_service.py`)

**Purpose**: Business logic + ORM → DTO mapping.

```python
# Public Methods
get_products_list(page, limit) → CatalogSearchResponseDTO
get_product_detail(product_id) → Optional[ProductDetailDTO]
search(query, thema_code, product_form, page, limit) → CatalogSearchResponseDTO
```

**Business Rules**:
- Only active products (status: '04', '02')
- Enum mapping (ProductForm → ProductType)
- Label enrichment via OnixCodeService
- Pagination calculation

**Key Patterns**:
- Repository injection (`self.repo = ProductRepository(session)`)
- Private mappers (`_to_product_card`, `_to_product_detail`)
- Data aggregation from multiple ORM relationships

---

### 3. Router Layer (`app/routers/catalog.py`)

**Purpose**: FastAPI endpoints + request validation.

```
GET  /api/v1/products?page=1&limit=20
GET  /api/v1/products/{id}
GET  /api/v1/search?q=text&thema=Y&format=BB&page=1&limit=20
```

**Request Validation**:
- Query parameters with validation
- Path parameters with type hints
- Automatic OpenAPI schema generation

**Response Contracts**:
- All responses as Pydantic DTOs
- Automatic JSON serialization
- 404 handling with HTTPException

---

### 4. Main Application (`main.py`)

**Purpose**: FastAPI app orchestration + lifecycle management.

```python
# Key Components
- CORS middleware
- Router registration
- Health check endpoint
- Global exception handler
- Lifespan context manager
```

---

## Data Flow Example

### GET /api/v1/products?page=1&limit=20

```
1. FastAPI Router (catalog.py)
   ↓ Validates: page=1, limit=20
   ↓ Creates: CatalogService(session)
   
2. CatalogService
   ↓ Calls: repo.get_all(limit=20, offset=0)
   
3. ProductRepository
   ↓ Executes: SELECT * FROM catalog_products LIMIT 20
   ↓ Returns: (List[CatalogProduct], total_count=103)
   
4. CatalogService (back)
   ↓ For each product:
     - Map ORM → ProductCardDTO
     - Get format label: OnixCodeService.get_label(150, "BB") → "Cloth over boards"
     - Get status: map_status("04") → {is_buyable: true, is_archived: false}
   
5. FastAPI Router (back)
   ↓ Returns: CatalogSearchResponseDTO
     {
       "total": 103,
       "page": 1,
       "limit": 20,
       "items": [ProductCardDTO, ...]
     }
   
6. Uvicorn
   ↓ JSON serializes Pydantic model
   ↓ HTTP 200 + Content-Type: application/json
```

---

## Search Endpoint Example

### GET /api/v1/search?q=Гришем&thema=Y&page=1

```
ProductRepository.search(
    query="Гришем",
    thema_code="Y",
    product_form=None,
    limit=20,
    offset=0
)

SQL Generated (pseudo-code):
  SELECT p.*
  FROM catalog_products p
  LEFT JOIN catalog_titles t ON p.id = t.product_id
  LEFT JOIN catalog_subjects s ON p.id = s.product_id
  WHERE p.publishing_status IN ('04', '02')
    AND t.title_text ILIKE '%Гришем%'
    AND s.subject_code LIKE 'Y%'
  ORDER BY p.created_at DESC
  LIMIT 20 OFFSET 0

Result: (List[CatalogProduct], total_count=5)
  ↓ Service maps to DTOs
  ↓ Returns CatalogSearchResponseDTO with 5 items
```

---

## Database Integration

### AsyncSession Pattern

```python
# In router:
async def list_products(session: AsyncSession = Depends(get_session)):
    service = CatalogService(session)
    return await service.get_products_list()

# get_session from app/core/database.py
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

### Query Examples

**Full product with all relationships**:
```python
stmt = select(CatalogProduct).where(
    CatalogProduct.id == product_id
)
product = await session.execute(stmt)
product = product.scalar_one_or_none()

# Access relationships:
product.titles[0].title_text
product.subjects[*].subject_heading_text
product.contributors[*].contributor.name
```

---

## Testing

**Test Coverage**: 14/14 ✅

```bash
# Run all tests
pytest tests/ -v

# Run only API tests
pytest tests/test_api_layers.py -v

# Health check works
curl http://localhost:8000/health
```

---

## Running the Server

```bash
# Development (auto-reload)
python main.py

# Production (with gunicorn)
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker

# Docker
docker build -t onix-api .
docker run -p 8000:8000 onix-api

# Test endpoints
curl http://localhost:8000/api/v1/products?page=1&limit=5
curl http://localhost:8000/api/v1/products/[id]
curl 'http://localhost:8000/api/v1/search?q=Гришем'
```

---

## Next Steps

- [ ] Add authentication (JWT tokens)
- [ ] Add rate limiting
- [ ] Add caching layer (Redis)
- [ ] Generate OpenAPI documentation
- [ ] Deploy to production

---

## Files Created/Modified

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | 85 | FastAPI app entry point |
| `app/services/catalog_service.py` | 245 | Business logic & DTO mapping |
| `app/routers/catalog.py` | 105 | API endpoints |
| `app/routers/__init__.py` | 5 | Router exports |
| `app/repositories/__init__.py` | 5 | Repository exports |
| `app/core/database.py` | ±2 | Added `get_session` alias |
| `tests/test_api_layers.py` | 90 | API layer tests |

---

## Key Dependencies

- **FastAPI**: Web framework
- **SQLAlchemy 2.x**: Async ORM
- **Pydantic v2**: DTO validation & serialization
- **Uvicorn**: ASGI server
- **PostgreSQL**: Database

