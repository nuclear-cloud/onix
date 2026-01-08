# Database Structure & Loaders Guide

**Last Updated:** January 6, 2026  
**Project:** ONIX Aggregator for Ukrainian Bookstores  
**Architecture:** V3.0 (Strict ONIX 3.0 Compliance)

---

## 📍 File Locations

```
onix_project/
├── app/
│   ├── models/
│   │   ├── catalog.py         ← Catalog schema (ONIX metadata)
│   │   ├── market.py          ← Market schema (prices/stock)
│   │   └── codes_v71.py       ← ONIX 3.71 code lists (enums)
│   │
│   └── services/
│       ├── catalog_loader.py  ← ETL from ONIX → Catalog tables
│       └── market_loader.py   ← Price/stock updates → Market tables
│
└── docs/
    └── DB_SCHEMA.md           ← Detailed schema docs
```

---

## 🏗️ Database Architecture Overview

The database is split into **two independent domains**:

### 1. **CATALOG Domain** (Static, Normalized ONIX)
- **Purpose:** "Golden Record" - fully normalized ONIX 3.0 structure
- **Update Frequency:** Low (book metadata changes rarely)
- **Data Type:** Structured, relational, fully normalized
- **Key Tables:** `catalog_products`, `catalog_titles`, `catalog_contributors`, `catalog_collections`, `catalog_subjects`, etc.

### 2. **MARKET Domain** (Dynamic, High-Frequency)
- **Purpose:** Real-time prices, stock availability from different suppliers
- **Update Frequency:** High (prices change hourly/daily)
- **Data Type:** Time-series data (current state + history)
- **Key Tables:** `suppliers`, `offers` (current prices), `price_history` (audit trail)

### 3. **REFERENCE Domain** (Dictionaries)
- `ref_thema_subjects` — THEMA classification system (UK v1.6)
- `ref_onix_codelists` — ONIX code mappings (loaded from XML)

**Load references**: `python scripts/load_reference_codes.py` (uses `DATABASE_URL`, auto-creates tables, truncates then bulk-loads from `data/ONIX_BookProduct_Codelists_Issue_71.json` and `data/thema_v1.6_uk.json`).

**Validation hook**: `CatalogLoader` skips THEMA subjects whose codes are absent in `ref_thema_subjects` to avoid dangling refs; non-THEMA schemes pass through unchanged. Ensure references are loaded before ingesting ONIX.

---

## 📊 CATALOG Domain Schema

### Core Entity: `catalog_products`

```
catalog_products
├── id (UUID, PK)
├── record_reference (VARCHAR, unique)      ← Book ID from publisher
├── isbn_13 (VARCHAR, unique)               ← 13-digit ISBN
├── ean (VARCHAR, unique)                   ← European Article Number
├── sku (VARCHAR)                           ← Stock-keeping unit
├── product_form (ENUM)                     ← 'BB'=Hardback, 'BC'=Paperback
├── product_form_detail (VARCHAR)
├── edition_number (INTEGER)
├── publishing_status (ENUM)                ← '04'=Active, '00'=Unspecified
├── notification_type (ENUM)                ← '03'=Update confirmed
├── is_ukrainian (BOOLEAN)                  ← Ukrainian content flag
├── publisher_id (UUID, FK → catalog_publishers)
├── onix_full (JSONB)                       ← Full ONIX dump (fallback)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)
```

### Related Catalog Tables

#### `catalog_publishers`
- Normalized publisher registry
- One publisher → many products (1:N)
- Deduplication on `name` (unique constraint)

#### `catalog_titles` (1:N from products)
```
├── product_id (FK)
├── type (ENUM TitleType)           ← '01'=Distinctive, '02'=Abbreviated
├── title_text (VARCHAR 1000)       ← Main title
├── subtitle (VARCHAR 1000)         ← Subtitle
```

#### `catalog_contributors` + `catalog_product_contributors_link` (M:N)
```
Contributors (Registry):
├── id (UUID, PK)
├── name (VARCHAR 255, indexed)     ← "Stephen King"
├── person_name_inverted (VARCHAR)  ← "King, Stephen"
└── biographical_note (TEXT)

Link Table:
├── product_id (FK, PK)
├── contributor_id (FK, PK)
├── role (ENUM ContributorRole)     ← 'A01'=Author, 'B06'=Translator
└── sequence_number (INTEGER)       ← Order in product
```

#### `catalog_collections` + `catalog_product_collections_link` (M:N)
```
Collections (Series):
├── title (VARCHAR 1000, indexed)   ← "Українська класика в коміксах"
├── type (ENUM CollectionType)      ← '10'=Publisher Series
└── issn (VARCHAR 8)

Link Table:
├── product_id (FK, PK)
├── collection_id (FK, PK)
└── sequence_number (VARCHAR)       ← "Vol. 1", "Book 3"
```

#### `catalog_subjects`
```
├── product_id (FK)
├── scheme_identifier (ENUM)        ← '24'=Proprietary, '01'=ONIX Thema
├── subject_code (VARCHAR)          ← "FL" (Fiction), "JFD" (Children's)
├── subject_heading_text (TEXT)     ← User-readable subject
```

#### Other Detail Tables
- `catalog_languages` — Language code (e.g., 'ukr', 'eng') + role
- `catalog_extents` — Pages, duration (values with units)
- `catalog_measures` — Dimensions (height, width) with units
- `catalog_text_content` — Descriptions, reviews
- `catalog_publishing_dates` — Publication date, edition release date
- `catalog_audience_ranges` — Age ranges, reading levels
- `catalog_prizes` — Award/prize information
- `catalog_related_products` — Product relations (sequel, part of series, etc.)

---

## 💰 MARKET Domain Schema

### Core Entity: `offers` (Current Market State)

```
offers (Hot Table - High Update Frequency)
├── id (UUID, PK)
├── book_id (UUID, FK → catalog_products.id, indexed)
├── supplier_id (UUID, FK → suppliers.id)
├── sku (VARCHAR 100)               ← Supplier's product ID
├── url (TEXT)                      ← Product URL at supplier
├── price (DECIMAL 10,2)            ← Current price
├── price_old (DECIMAL 10,2)        ← Previous/discount price
├── currency (VARCHAR 3, default 'UAH')
├── availability (ENUM)             ← '20'=In-stock, '21'=Out-of-stock
├── in_stock (BOOLEAN)              ← Convenience flag
└── last_updated (TIMESTAMP)        ← When price was last checked
```

### Supporting Tables

#### `suppliers`
```
├── id (UUID, PK)
├── name (VARCHAR 255)              ← "Yakaboo", "Knygarnya Ye"
├── code (VARCHAR 50, unique)       ← "yakaboo", "knygarnya-ye"
├── base_url (VARCHAR 500)          ← https://yakaboo.ua
└── is_active (BOOLEAN, default=true)
```

#### `price_history` (Audit Trail)
```
├── id (UUID, PK)
├── offer_id (UUID, FK → offers.id)
├── price (DECIMAL 10,2)            ← Historical price
├── currency (VARCHAR 3)
├── availability (ENUM)
└── recorded_at (TIMESTAMP)         ← When recorded

NOTE: For PostgreSQL partitioning, this table can be partitioned by 
      recorded_at (range partitions by month/quarter) to handle large volumes.
```

---

## 🔄 CATALOG LOADER Algorithm

**File:** `app/services/catalog_loader.py`  
**Purpose:** Transform ONIX 3.0 JSON → Normalized Relational Tables

### Entry Point: `load_product(onix: OnixProduct) -> UUID`

```
┌─────────────────────────────────────────┐
│ Input: OnixProduct (Pydantic Schema)    │
│        - product_identifier[]           │
│        - title_detail[]                 │
│        - contributor[]                  │
│        - collection[]                   │
│        - subject[]                      │
│        - extent[], measure[], language[]│
└─────────────────────────────────────────┘
              ↓
┌─ STEP 1: Identify Product ──────────────┐
│ 1. Extract ISBN-13 from product_identifier
│ 2. Extract EAN-13 (GTIN)
│ 3. Get proprietary ID (record_reference)
│ 4. Check if product exists in DB:
│    - Try ISBN-13 lookup
│    - Fall back to record_reference lookup
│ 5. If found: use existing product (update mode)
│    If not found: create new CatalogProduct
└─────────────────────────────────────────┘
              ↓
┌─ STEP 2: Populate Core Fields ──────────┐
│ Set direct attributes:
│  • record_reference
│  • isbn_13
│  • ean
│  • sku
│  • product_form (e.g., 'BB' = Hardback)
│  • onix_full (full JSON dump for fallback)
│ Lookup & Link:
│  • publisher_id (get_or_create_publisher)
└─────────────────────────────────────────┘
              ↓
┌─ STEP 3: Flush & Get ID ────────────────┐
│ session.flush() → Generate UUID for new
│ Use product.id for child inserts
└─────────────────────────────────────────┘
              ↓
┌─ STEP 4: Clear Old Relations ───────────┐
│ If updating existing product:
│  • DELETE all related titles
│  • DELETE all related contributors
│  • DELETE all related collections
│  • DELETE all related subjects
│  • DELETE all related languages, extents
│  • DELETE all measures, text content
│ Reason: Ensure clean re-insertion
└─────────────────────────────────────────┘
              ↓
┌─ STEP 5: Process Child Tables ──────────┐
│
│ A. Titles (_process_titles)
│    └─ For each title_detail:
│       ├─ Extract title_text, subtitle
│       ├─ Store title_type (e.g., '01'=Distinctive)
│       └─ INSERT into catalog_titles
│
│ B. Contributors (_process_contributors)
│    └─ For each contributor:
│       ├─ Get or create contributor in registry
│       ├─ Extract role (e.g., 'A01'=Author)
│       ├─ Store sequence_number
│       └─ Link via catalog_product_contributors_link
│
│ C. Collections (_process_collections)
│    └─ For each collection:
│       ├─ Extract collection title
│       ├─ Get or create collection in registry
│       ├─ Extract sequence_number (e.g., 'Vol. 5')
│       └─ Link via catalog_product_collections_link
│
│ D. Subjects (_process_subjects)
│    └─ For each subject:
│       ├─ Extract subject_scheme_identifier
│       ├─ Store subject_code (e.g., 'FL' for Fiction)
│       ├─ Store subject_heading_text
│       └─ INSERT into catalog_subjects
│
│ E. Details (_process_details)
│    ├─ Languages: code + role
│    ├─ Extents: pages (type + value + unit)
│    ├─ Measures: dimensions (height, width)
│    └─ Text Content: descriptions, reviews
│
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Output: product.id (UUID)               │
│ All child records are committed         │
│ Product ready for market data linking   │
└─────────────────────────────────────────┘
```

### Key Helper Methods

#### `_extract_id(onix, type_code) -> Optional[str]`
- Loops through `product_identifier[]` array
- Matches `product_id_type == type_code` (e.g., ProductIdentifierType.ISBN_13)
- Returns the matching `id_value` or None

#### `_find_product(isbn13, ref) -> Optional[CatalogProduct]`
- First tries ISBN-13 lookup (most reliable)
- Falls back to `record_reference` lookup
- Returns existing product or None (for create)

#### `_get_or_create_publisher(name) -> UUID`
- **Caching:** In-memory `_publisher_cache[name]` within transaction scope
- Looks up publisher by exact name match
- If not found, creates new Publisher and stores in cache
- Returns publisher UUID

#### `_get_or_create_contributor(name) -> UUID`
- **Normalization:** `name.strip()` 
- **Caching:** In-memory `_contributor_cache[clean_name]`
- Similar to publisher lookup
- Returns contributor UUID

### Performance Optimizations

1. **In-Transaction Caching**
   - `_publisher_cache`, `_contributor_cache`, `_collection_cache`
   - Avoids repeated DB lookups within same transaction
   - Cache scope: per `load_product()` call

2. **Batch Operations**
   - Multiple `session.add()` calls, single commit
   - `session.flush()` after core record creation (to get ID)
   - Child records added before final flush/commit

3. **Deduplication**
   - Publisher/Contributor lookups by unique field (name)
   - Collection lookups by title
   - M:N linking tables prevent duplicates

---

## 💵 MARKET LOADER Algorithm

**File:** `app/services/market_loader.py`  
**Purpose:** High-frequency price & stock updates with audit trail

### Entry Point: `update_price(...) -> None`

```
Input Parameters:
├── book_id (UUID)           ← Which book in catalog
├── supplier_code (str)      ← "yakaboo", "knygarnya-ye"
├── sku (str)                ← Supplier's product ID
├── price (float)            ← Current price
├── url (str)                ← Product page URL
├── in_stock (bool)          ← Is it available?
├── currency (str)           ← Default "UAH"
└── price_old (float, opt)   ← Previous price (for discounts)

┌─────────────────────────────────────────┐
│ STEP 1: Get or Create Supplier          │
│                                         │
│ supplier_id = await get_supplier_id(    │
│     code = "yakaboo",                   │
│     name = "Yakaboo",                   │
│     base_url = "https://yakaboo.ua"     │
│ )                                       │
│                                         │
│ Process:                                │
│ 1. Check _supplier_cache[code]          │
│ 2. If found: return cached ID           │
│ 3. Otherwise: SELECT from suppliers     │
│ 4. If not in DB: CREATE new Supplier    │
│ 5. Cache the ID for next calls          │
│                                         │
│ Benefit: Supplier lookup is typically   │
│          1-10 unique suppliers          │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ STEP 2: Upsert Offer (Current Price)    │
│                                         │
│ Use PostgreSQL INSERT ... ON CONFLICT   │
│                                         │
│ Insert Values:                          │
│  • book_id, supplier_id                 │
│  • sku, url                             │
│  • price, price_old                     │
│  • currency, in_stock                   │
│  • availability (derived from in_stock) │
│  • last_updated = NOW()                 │
│                                         │
│ Unique Key: (book_id, supplier_id)      │
│                                         │
│ On Conflict:                            │
│  • Update: price, price_old, in_stock,  │
│           availability, url, last_updated
│  • Preserve: offer_id, created_at       │
│                                         │
│ Return: offer_id (for history logging)  │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ STEP 3: Log to Price History            │
│                                         │
│ Create PriceHistory record:             │
│  • offer_id (from upsert)               │
│  • price (current)                      │
│  • currency                             │
│  • availability (enum)                  │
│  • recorded_at = NOW()                  │
│                                         │
│ session.add(history)                    │
│                                         │
│ Purpose: Audit trail for price trends   │
│ DB Optimization: Can be partitioned by  │
│                 recorded_at for large   │
│                 volume datasets         │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Output: PriceHistory record created     │
│ Offer table is updated (current state)  │
│ History is preserved for analytics      │
└─────────────────────────────────────────┘
```

### Helper Methods

#### `get_supplier_id(code, name, base_url) -> UUID`
- **Caching:** In-memory `_supplier_cache[code]`
- Query suppliers by unique `code`
- Create if not exists
- Return cached UUID for subsequent calls

### SQL Strategy: PostgreSQL `INSERT ... ON CONFLICT`

```sql
INSERT INTO offers (
    book_id, supplier_id, sku, url,
    price, price_old, currency, in_stock,
    availability, last_updated
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())
ON CONFLICT (book_id, supplier_id) DO UPDATE
    SET price = EXCLUDED.price,
        price_old = EXCLUDED.price_old,
        in_stock = EXCLUDED.in_stock,
        last_updated = NOW(),
        url = EXCLUDED.url
RETURNING id;
```

**Benefits:**
- Atomic operation (no race condition)
- Handles concurrent updates safely
- Single DB round-trip
- Perfect for high-frequency updates

### Why Separate Current + History?

| Scenario | offers | price_history |
|----------|--------|---------------|
| Get current price | ✅ Fast (indexed) | ❌ Scan entire history |
| Track price trends | ❌ Only current | ✅ Complete audit trail |
| Detect price drop | ✅ Compare with previous | ✅ See all changes |
| Analytics/reporting | ⚠️ Limited | ✅ Rich data |
| Storage efficiency | ✅ 1 row/book/supplier | ⚠️ Many rows (time-series) |

---

## 🔗 Data Flow: From ONIX to Market

```
                    Ukrainian Bookstore APIs
                    (Yakaboo, Knygarnya Ye, Vivat)
                              ↓
                    [ONIX XML / JSON Scraper]
                              ↓
                    OnixProduct (Pydantic)
                              ↓
              ┌───────────────────────────────────┐
              │                                   │
              ↓                                   ↓
    CATALOG_LOADER                    MARKET_LOADER
    (Static Data)                      (Dynamic Data)
              │                                   │
              ├─ catalog_products                ├─ offers
              ├─ catalog_titles                  ├─ price_history
              ├─ catalog_contributors            ├─ suppliers
              ├─ catalog_collections             │
              ├─ catalog_subjects                │
              └─ catalog_*                       │
                                                 │
                    ┌──────────────────────────────┘
                    │
                    ↓
            [Unified Product Record]
            - ISBN links both domains
            - Join on: catalog_products.id = offers.book_id
```

---

## 📈 Scaling Considerations

### For CATALOG (Static Growth)
- **Growth Rate:** ~5-10K new books/month (Ukrainian market)
- **Query Patterns:** Mostly reads (lookups by ISBN, title)
- **Indexes:** 
  - `catalog_products.isbn_13`
  - `catalog_products.record_reference`
  - `catalog_contributors.name`
  - `catalog_collections.title`

### For MARKET (High Write Volume)
- **Growth Rate:** 100K-1M price updates/day (10+ suppliers checking continuously)
- **Query Patterns:** High writes, occasional reads
- **Optimizations:**
  - `offers` index on `(book_id, supplier_id)`
  - `price_history` can be partitioned by `recorded_at`
  - Consider archiving old price_history data (>1 year) to separate tables

### Database Connection Pool
- Use async SQLAlchemy with connection pooling
- Recommended pool size: 10-20 connections
- Set `pool_recycle=3600` (connection age limit)

---

## 🐛 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Duplicate products | ISBN-13 collision | Add ISBN validation before insert |
| Slow title lookups | Missing index | Add index on `catalog_titles.title_text` |
| Price updates slow | High lock contention on `offers` | Use PostgreSQL `SKIP LOCKED` or partitioning |
| History table bloats | No archival policy | Archive price_history >90 days to cold storage |
| Contributor dedup fails | Case-sensitive name matching | Add `LOWER(name)` in uniqueness check |
| OOM during large inserts | Loading all in memory | Use batch processing (1000 records at a time) |

---

## 📝 Usage Examples

### Load a Single Product
```python
from app.schemas.onix_full import OnixProduct
from app.services.catalog_loader import CatalogLoader
from app.core.database import get_session

async def example():
    async with get_session() as session:
        loader = CatalogLoader(session)
        
        onix_product = OnixProduct(...)  # Construct from JSON
        product_id = await loader.load_product(onix_product)
        
        await session.commit()
        print(f"Product loaded: {product_id}")
```

### Update Prices from Yakaboo
```python
from app.services.market_loader import MarketLoader

async def example():
    async with get_session() as session:
        loader = MarketLoader(session)
        
        await loader.update_price(
            book_id=UUID("..."),
            supplier_code="yakaboo",
            sku="12345",
            price=199.99,
            url="https://yakaboo.ua/...",
            in_stock=True,
            currency="UAH",
            price_old=249.99
        )
        
        await session.commit()
```

---

## 📚 Related Documentation

- [DB Schema Details](DB_SCHEMA.md)
- [ONIX Standard](https://www.editeur.org/83/ONIX/)
- [THEMA Classification](https://www.thema.info/)
- [PostgreSQL ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html)

