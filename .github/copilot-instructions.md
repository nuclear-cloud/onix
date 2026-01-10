# Copilot Instructions - ONIX Aggregator

## Project Overview

**ONIX Aggregator** is a high-performance book metadata & pricing system for Ukrainian bookstores with dual capabilities:
1. **REST API** for querying catalogued books (FastAPI + 3-tier architecture)
2. **Web crawler** for discovering & extracting product data from retailers

**69k+ Ukrainian books | Prisma ORM | PostgreSQL + async/await**

---

## Architecture: The Big Picture

### Three Layers (Prisma ORM)

**1. Repository Layer** (`app/repositories/prisma_repositories.py`)
- Pure data access via Prisma client
- `PrismaProductRepository.get_all()`, `search()`, `get_by_isbn()`
- Returns Prisma models; handles includes/relations

**2. Service Layer** (`app/services/`)
- Business rules + ORM → dict/DTO mapping
- `PrismaCatalogService.get_catalog()` calculates pagination, enriches data
- Injects Prisma client

**3. Router Layer** (`app/routers/catalog.py`)
- FastAPI endpoints with request validation
- Routes: `GET /catalog/products`, `/catalog/products/{isbn13}`, `/catalog/search`
- Returns dicts/DTOs; automatic OpenAPI schema

**Data Flow**: `Router` → `PrismaCatalogService(db)` → `PrismaProductRepository` → DB → Map → Response

### Database: Two Schemas

- **public**: Main product data (catalog_products, Contributor, Subject, etc.)
- **codelist**: ONIX reference codes (product_form, publishing_status, etc.)

### ORM: Prisma Only

- **Prisma** (`prisma/schema.prisma`, `0.15.0`): All database operations
  - Run `prisma generate` after schema changes
  - Run `prisma db push` for schema sync (dev)
  - Multi-schema support enabled

---

## Development Quick Start

```bash
# 1. Setup
cd onix_project && source .venv/bin/activate

# 2. Database (required)
cat > .env << 'EOF'
DATABASE_URL=postgresql://onix_user:onix_pass@localhost:5432/onix_db
PRISMA_DATABASE_URL=postgresql://onix_user:onix_pass@localhost:5432/onix_db
EOF

# 3. Generate Prisma client
prisma generate

# 4. Run API
python main.py  # FastAPI on :8000/docs

# 5. Test
pytest tests/ -v
```

---

## Key Patterns & Rules

### 1. Prisma Client Usage

```python
from prisma import Prisma
from app.core.prisma_db import get_db

# In router - dependency injection
@router.get("/products")
async def list_products(db: Prisma = Depends(get_db)):
    products = await db.catalogproduct.find_many(
        take=20,
        include={"contributors": True, "subjects": True}
    )
    return products
```

### 2. Services: Inject Prisma Client

```python
class PrismaCatalogService:
    def __init__(self, db: Prisma):
        self.db = db
        self.product_repo = PrismaProductRepository(db)
    
    async def get_catalog(self, limit, offset):
        products, total = await self.product_repo.get_all(limit, offset)
        return {"total": total, "items": products}
```

### 3. Routers: Dependency Injection

```python
from app.core.prisma_db import get_db

@router.get("/products")
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Prisma = Depends(get_db),
) -> dict:
    service = PrismaCatalogService(db)
    return await service.get_catalog(limit, (page-1)*limit)
```

### 4. N:N Relations (Contributors, Subjects)

```python
# Contributors are N:N via ProductContributor junction
product = await db.catalogproduct.find_unique(
    where={"isbn13": isbn},
    include={
        "contributors": {
            "include": {"contributor": True}
        },
        "subjects": {
            "include": {"subject": True}
        }
    }
)

# Get all books by an author
contributor = await db.contributor.find_first(
    where={"person_name": "Тарас Шевченко"},
    include={"products": {"include": {"product": True}}}
)
```

### 5. ONIX Conventions

- **Field naming**: `isbn13`, `product_form_code`, `language_code`
- **Enums**: Defined in `app/models/codes_v71.py`
- **Scheme codes**: 20=Keywords, 24=Proprietary categories, 93=Thema

---

## Common Tasks

### Adding a New API Endpoint

1. **Add repository method** (`app/repositories/prisma_repositories.py`)
   ```python
   async def filter_by_format(self, form_code: str, limit: int):
       return await self.db.catalogproduct.find_many(
           where={"product_form_code": form_code},
           take=limit
       )
   ```

2. **Add service method** (`app/services/prisma_catalog_service.py`)
   ```python
   async def get_by_format(self, form_code: str):
       products = await self.product_repo.filter_by_format(form_code, 100)
       return [self._format_product(p) for p in products]
   ```

3. **Add router endpoint** (`app/routers/catalog.py`)
   ```python
   @router.get("/products/format/{form_code}")
   async def list_by_format(form_code: str, db: Prisma = Depends(get_db)):
       service = PrismaCatalogService(db)
       return await service.get_by_format(form_code)
   ```

### Modifying Schema

1. Edit `prisma/schema.prisma`
2. Run `prisma generate` to update client
3. Run `prisma db push` (dev) or create migration
4. Update DTOs in `app/schemas/` if needed

---

## Testing Patterns

```bash
pytest tests/ -v  # All tests
```

**Test structure**:
- Mock Prisma client for unit tests
- Use `@pytest.mark.asyncio` for async tests

---

## File Reference

| Path | Purpose |
|------|---------|
| `main.py` | FastAPI app + lifespan + CORS |
| `app/core/prisma_db.py` | Prisma client + get_db dependency |
| `app/models/codes_v71.py` | ONIX code Enums |
| `app/repositories/prisma_repositories.py` | Data access layer |
| `app/services/prisma_catalog_service.py` | Business logic |
| `app/services/prisma_ingestion_service.py` | Data import |
| `app/routers/catalog.py` | FastAPI endpoints |
| `app/schemas/*.py` | Pydantic DTOs |
| `prisma/schema.prisma` | Database schema |
| `scripts/import_yakaboo_prisma.py` | Import script |

---

## Database Stats

| Table | Count |
|-------|-------|
| Products | 69,375 |
| Unique Contributors | 26,879 |
| Unique Subjects | 54,129 |
| Product-Contributor links | 88,084 |
| Product-Subject links | 604,207 |

---

## References

- **API Docs**: `http://localhost:8000/docs` (OpenAPI)
- **Prisma Studio**: `npx prisma studio`
- **docs/YAKABOO_SIMPLE_MAPPING.md**: Field mapping reference
- **docs/DB_SCHEMA.md**: Full table schema
