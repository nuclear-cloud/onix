# ONIX Aggregator (V2 Architecture)

**Centralized Book Catalog & Price Aggregator for Ukraine**

This project implements a high-performance system for aggregating book metadata and prices from multiple retailers, strictly adhering to the **ONIX for Books 3.0** standard.

## 🏗 Architecture

The system uses a **Hybrid Database Architecture** split into two domains:

### 1. Catalog (Static Data)
Stores the "Golden Record" for each book. Optimized for complex search and filtering.
*   **Source of Truth**: ONIX 3.0 Standard.
*   **Storage**: Normalized SQL tables (`catalog_products`, `catalog_contributors`...) + JSONB backup.
*   **Models**: `app/models/catalog.py`

### 2. Market (Dynamic Data)
Stores high-frequency price and availability updates.
*   **Focus**: Speed and freshness.
*   **Storage**: Hot table (`offers`) for current state + Cold table (`price_history`) for logs.
*   **Models**: `app/models/market.py`

## 🛠 Tech Stack
*   **Language**: Python 3.10+
*   **Database**: PostgreSQL (Async/Await)
*   **ORM**: SQLAlchemy 2.0 (Async) + **Prisma** (Type-safe queries)
*   **Validation**: Pydantic v2
*   **Testing**: Pytest + Asyncio

## 🚀 Getting Started

### Prerequisites
*   PostgreSQL 14+
*   Python 3.10+

### Setup

1.  **Environment**:
    Copy `.env.example` to `.env` (if available) or create one:
    ```bash
    DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db_name
    PRISMA_DATABASE_URL=postgresql://user:pass@localhost:5432/db_name
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    prisma generate  # Generate Prisma client
    ```

3.  **Initialize Database**:
    ⚠️ **Warning**: This destroys existing data.
    ```bash
    python scripts/init_final_db.py --force
    ```

## 🧪 Testing

Run the integration tests to verify DB models and relations:

```bash
# Ensure PYTHONPATH includes the root directory
PYTHONPATH=. pytest tests/test_db_models.py -v
```

## 🔍 Prisma Integration

The project supports **dual ORMs** - both SQLAlchemy and Prisma. Prisma provides type-safe, modern database queries:

```bash
# Quick test
python test_prisma.py

# Run examples
python examples/prisma_simple.py
python examples/prisma_advanced.py
```

**Documentation:**
- [Prisma Complete Guide](./docs/PRISMA_GUIDE.md) - Full documentation
- [Prisma Quick Reference](./docs/PRISMA_QUICKREF.md) - Syntax cheat sheet
- [Integration Summary](./PRISMA_INTEGRATION_COMPLETE.md) - What was done

**Quick Example:**
```python
from prisma import Prisma

async def query():
    db = Prisma()
    await db.connect()
    
    # Type-safe queries with auto-completion
    books = await db.catalogproduct.find_many(
        where={'isbn13': {'not': None}},
        include={'publisher': True, 'titles': True},
        take=10
    )
    
    await db.disconnect()
```

## 📂 Project Structure

```
onix_project/
├── app/
│   ├── models/          # SQLAlchemy Database Models
│   │   ├── catalog.py   # Static Book Data (ONIX)
│   │   ├── market.py    # Dynamic Prices (Offers)
│   │   └── codes.py     # ONIX Enum Definitions
│   ├── core/            # Config & DB Connection
│   └── scraper/         # Data Transformers
├── scripts/             # DevOps scripts (init_db, etc.)
├── tests/               # Integration & Unit tests
├── data/                # Local data files
└── archive/             # Legacy code (V1)
```

## 📚 Key Database Tables

| Domain | Table Name | Description |
| :--- | :--- | :--- |
| **Catalog** | `catalog_products` | Main book registry. Includes `onix_full` (JSONB). |
| | `catalog_titles` | All title variations (Original, Translated). |
| | `catalog_product_contributors` | Authors, Translators, Illustrators. |
| | `catalog_publishers` | Publisher registry. |
| **Market** | `offers` | Current price & stock status per store. |
| | `price_history` | Historical log of price changes. |
| | `suppliers` | Retailer registry (Yakaboo, Knygarnya Ye). |