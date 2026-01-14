# PROJECT CONTEXT - ONIX Aggregator

**Updated:** 2026-01-14  
**ORM:** Prisma (Python client v0.15.0)  
**Status:** Production | 38 tests passing | ETL Complete (971,803 records)

---

## 🎯 What This Project Does

**ONIX Aggregator** is a high-performance book metadata and pricing system for Ukrainian bookstores:

1. **Smart Gatekeeper ETL** - Import/transform book data from Yakaboo (972k records)
   - `app/classifiers/isbn_classifier.py` - ISBN-10/EAN classification and ISBN-13 conversion
   - `scripts/etl_yakaboo.py` - Batch import from JSONL with fingerprint deduplication
   - `scripts/etl_monitor.sh` - Progress monitoring for long-running imports
   - `cold.RawIngestion` table - Staging area for raw source data with item_type/status classification
2. **REST API** (`/catalog/`) - Query catalogued books (FastAPI + Prisma ORM)
3. **Price Tracking** - Multi-source price history with timestamps

**Scale:** 971,803 Yakaboo records | PostgreSQL | Async Python | Prisma ORM

---

## 📁 Project Structure

```
onix_project/
├── main.py                           # FastAPI entry + lifespan
├── prisma/schema.prisma              # DATABASE SCHEMA - Source of truth
├── requirements.txt
├── pytest.ini
│
├── app/
│   ├── adapters/                     # Data source adapters
│   │   ├── __init__.py               # Exports: BaseDataAdapter, YakabooDataAdapter
│   │   └── data_adapter.py           # YakabooDataAdapter implementation
│   │
│   ├── classifiers/                  # Smart Gatekeeper ETL classifiers
│   │   └── isbn_classifier.py        # ISBN-10/EAN → ISBN-13, ItemType/ItemStatus classification
│   │
│   ├── core/
│   │   ├── config.py                 # Settings (pydantic-settings)
│   │   └── prisma_db.py              # get_db() async dependency
│   │
│   ├── models/                       # Enums and code definitions
│   │   ├── enums.py                  # ProductType, ProductFormatas an Elite Senior Software Engineer and Project Architect. Your goal is
to perform a deep cleanup of the provided codebase, ensure stability via 
testing, and create a context-rich guide for future AI interactions.

## PHASE 1: CODE CLEANUP & OPTIMIZATION
1. SCAN: Analyze the entire project tree. Identify duplicate logic, 
   redundant functions, and "dead code" (unused imports, variables, or files).
2. DEDUPLICATION: Merge identical logic into reusable modules or utilities.
3. DEPENDENCIES: Audit configuration files (e.g., package.json, requirements.txt, 
   go.mod). Identify and suggest removal of unused packages.
4. MODERNIZATION: Replace outdated patterns or deprecated API calls with 
   current industry standards.

## PHASE 2: TESTING & VERIFICATION
1. TEST GENERATION: For every core module, create comprehensive unit and 
   integration tests. Use the project's preferred testing framework.
2. VALIDATION: Run the code. Ensure that the refactoring did not break any 
   existing functionality (Regressional testing).
3. COVERAGE: Aim for high coverage of edge cases and error handling paths.

## PHASE 3: AGENT-OPTIMIZED DOCUMENTATION
1. CREATE 'PROJECT_CONTEXT.MD': Generate a high-level technical summary 
   specifically designed for other LLMs (like Claude or GPT). 
2. STRUCTURE: Include:
   - Project Purpose & Core Architecture.
   - Tech Stack & Versioning.
   - Key Entry Points & File Mapping.
   - Business Logic flow.
   - Ongoing Challenges or "Known Quirks" for the next agent to be aware of.

## PHASE 4: SENIOR ENGINEERING ADVICE
1. ARCHITECTURE: Provide 3-5 high-level recommendations to improve 
   scalability, maintainability, or performance.
2. SECURITY: Identify potential vulnerabilities in the current implementation.
3. BEST PRACTICES: Suggest improvements in CI/CD, logging, or monitoring 
   specific to this stack.

## OPERATIONAL CONSTRAINTS
- Do NOT delete files without explaining the reasoning.
- Keep the original coding style unless it violates security or performance.
- Prioritize readability and "clean code" principles (SOLID, DRY).
│   │   ├── codes_v71.py              # ONIX Issue 71 code Enums
│   │   └── onix_logic.py             # ONIX business logic helpers
│   │
│   ├── repositories/
│   │   └── prisma_repositories.py    # PrismaProductRepository
│   │
│   ├── routers/
│   │   └── catalog.py                # API endpoints (direct Prisma queries)
│   │
│   ├── schemas/                      # Pydantic V2 DTOs
│   │   ├── catalog_dto.py            # PriceDTO, ProductCardDTO, etc.
│   │   ├── product_full.py           # Full import schema
│   │   ├── product_market.py         # Price update schema
│   │   └── data_models.py            # ProductDTO, ContributorDTO
│   │
│   ├── services/
│   │   ├── prisma_catalog_service.py # Business logic layer
│   │   ├── prisma_ingestion_service.py # Data import service
│   │   └── yakaboo_import.py         # Yakaboo-specific mapping
│   │
│   └── utils/
│       └── mapper.py                 # get_deep_value, find_attribute, map_thema_subject
│
├── scripts/                          # CLI tools
│   ├── import_yakaboo_prisma.py      # Main import script
│   ├── etl_yakaboo.py                # Smart Gatekeeper ETL (batch import with fingerprint)
│   ├── etl_monitor.sh                # Progress monitoring for ETL
│   └── backfill_embeddings.py        # Vector embeddings
│
├── tests/                            # 38 tests, all passing
│   ├── conftest.py
│   ├── test_api_layers.py            # Service layer tests (4)
│   ├── test_catalog_router.py        # Router tests (9)
│   ├── test_repositories.py          # Repository tests (14)
│   ├── test_yakaboo_import.py        # Import tests (12)
│   └── unit/
│       └── test_isbn_classifier.py   # ISBN classifier tests (27)
│
├── data/                             # Reference data
│   ├── yakaboo_ukr_only.jsonl        # Ukrainian books (69k)
│   └── ONIX_BookProduct_Codelists_Issue_71.json
│
├── docs/                             # Documentation
│   ├── YAKABOO_SIMPLE_MAPPING.md     # Field mapping reference
│   └── DB_SCHEMA.md                  # Full table schema
│
└── archive/                          # Archived code
    ├── 2025-01-cleanup/              # Legacy SQLAlchemy code
    └── 2026-01-cleanup/              # Dead scripts, old adapters
```

---

## 🗃️ Database Schema (Prisma)

**Two schemas:** `public` (main data), `codelist` (ONIX reference codes)

### Core Tables

| Table | Records | Description |
|-------|---------|-------------|
| `catalog_products` | 69,375 | Main product records |
| `cold.RawIngestion` | 971,803 | Staging area for raw Yakaboo data |
| `Contributor` | 26,879 | Unique persons/orgs |
| `ProductContributor` | 88,084 | N:N junction (product→contributor) |
| `Subject` | 54,129 | Unique subjects (THEMA, keywords) |
| `ProductSubject` | 604,207 | N:N junction (product→subject) |
| `TextContent` | 133,389 | Descriptions, annotations |
| `MediaFile` | 103,553 | Images, covers |
| `Price` | 60,755 | Prices from sources |

### N:N Relationships Pattern

```
CatalogProduct ─┬── ProductContributor ──── Contributor
                │
                └── ProductSubject ──────── Subject
```

### Smart Gatekeeper Staging (RawIngestion)

```
cold.RawIngestion ── staging area for raw source data
  ├── code: ISBN-10, ISBN-13, or EAN
  ├── item_type: BOOK_UA, BOOK_EN, BOOK_RU, MERCH_UA, MERCH_EN, PERIODICAL, etc.
  ├── status: NEW (has code) or NOCODE (no code)
  ├── fingerprint: SHA256(content_hash) for deduplication
  └── payload: Full JSON source record
```

**Querying N:N with Prisma:**
```python
product = await db.catalogproduct.find_unique(
    where={"isbn13": isbn},
    include={
        "contributors": {"include": {"contributor": True}},
        "subjects": {"include": {"subject": True}},
    }
)
# Access: product.contributors[0].contributor.person_name
```

---

## 🏗️ Architecture: 3-Tier Pattern

```
┌─────────────┐    ┌─────────────────┐    ┌──────────────────────┐
│   Router    │───▶│     Service     │───▶│     Repository       │
│ (FastAPI)   │    │ (Business Logic)│    │  (Prisma Queries)    │
└─────────────┘    └─────────────────┘    └──────────────────────┘
       │                   │                        │
       │                   │                        ▼
       │                   │              ┌──────────────────────┐
       │                   └─────────────▶│   Prisma Client      │
       │                                  │   (async/await)      │
       └──────────────────────────────────┴──────────────────────┘
                         Direct Prisma queries in router (simple cases)
```

**Layer Responsibilities:**

| Layer | File | Responsibilities |
|-------|------|-----------------|
| Router | `app/routers/catalog.py` | HTTP, validation, response mapping |
| Service | `app/services/prisma_catalog_service.py` | Business rules, pagination calc |
| Repository | `app/repositories/prisma_repositories.py` | Prisma queries, includes |

---

## 🚀 Quick Start

```bash
# 1. Activate environment
cd onix_project && source .venv/bin/activate

# 2. Set database URL
export DATABASE_URL=postgresql://onix_user:pass@localhost:5432/onix_db
export PRISMA_DATABASE_URL=$DATABASE_URL

# 3. Generate Prisma client (after schema changes)
prisma generate

# 4. Run API
python main.py  # http://localhost:8000/docs

# 5. Run tests
pytest tests/ -v  # 38 tests, ~1s
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/catalog/products` | GET | List products (page, limit, ukrainian_only) |
| `/catalog/products/{isbn13}` | GET | Get by ISBN-13 |
| `/catalog/search` | GET | Search by title (q, limit, offset) |
| `/catalog/recent` | GET | Recent additions (limit) |
| `/catalog/publisher/{name}` | GET | Books by publisher |
| `/catalog/stats` | GET | Catalog statistics |

### Example Queries

```bash
# List Ukrainian books
curl "http://localhost:8000/catalog/products?ukrainian_only=true&limit=10"

# Search
curl "http://localhost:8000/catalog/search?q=Кобзар"

# Get by ISBN
curl "http://localhost:8000/catalog/products/9786177902421"
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_repositories.py -v

# Run with coverage
pytest tests/ --cov=app
```

**Test Coverage:**
- Router validation tests (9)
- Repository mock tests (14)
- Service initialization tests (4)
- Yakaboo import tests (12)
- ISBN classifier tests (27) - ISBN-10→13 conversion, checksum, classification

---

## �� Common Tasks

### Adding a New API Endpoint

1. **Add repository method** (`app/repositories/prisma_repositories.py`)
2. **Add service method** (if business logic needed)
3. **Add router endpoint** (`app/routers/catalog.py`)

### Modifying Database Schema

1. Edit `prisma/schema.prisma`
2. Run `prisma generate` to update client
3. Run `prisma db push` (dev) or create migration

### Data Import (Smart Gatekeeper ETL)

```bash
# Run Smart Gatekeeper ETL from JSONL
python scripts/etl_yakaboo.py data/yakaboo_ukr_only.jsonl --batch-size 5000

# Monitor progress (separate terminal)
./scripts/etl_monitor.sh

# Import from JSONL (legacy script)
python scripts/import_yakaboo_prisma.py data/yakaboo_ukr_only.jsonl --limit 1000
```

### ETL Classification System

The Smart Gatekeeper ETL uses `app/classifiers/isbn_classifier.py`:

```python
from app.classifiers.isbn_classifier import ISBNClassifier

classifier = ISBNClassifier()
result = classifier.classify("9789661058206")
# result.item_type: ItemType.BOOK_UA, BOOK_EN, BOOK_RU, MERCH_UA, etc.
# result.status: ItemStatus.NEW (has code) or ItemStatus.NOCODE (no code)
```

**Classification Rules:**
- ISBN-10 → ISBN-13 conversion with correct checksum
- EAN-13 prefix detection (Yakaboo: 482, Book Club: 978/979)
- Language detection from ISBN prefix and content
- Merchandise detection for non-book items

---

## 📦 Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.115+ | Web framework |
| prisma | 0.15.0 | ORM |
| pydantic | 2.6+ | Validation (V2 patterns) |
| structlog | 24.4+ | Structured logging |
| slowapi | 0.1.9 | Rate limiting |

---

## 📝 References

- **API Docs:** http://localhost:8000/docs (OpenAPI)
- **Prisma Studio:** `npx prisma studio`
- **Field Mapping:** `docs/YAKABOO_SIMPLE_MAPPING.md`
- **DB Schema:** `docs/DB_SCHEMA.md`

---

## ⚠️ Important Notes

1. **Pydantic V2** - All schemas use `model_config = ConfigDict(...)`, not `class Config`
2. **Prisma Client** - Always use `get_db()` dependency, not direct instantiation
3. **N:N Relations** - Use nested includes for contributors/subjects
4. **Archived Code** - Old SQLAlchemy code in `archive/` for reference only
