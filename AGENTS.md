# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-17
**Status:** Active Development

## OVERVIEW
**ONIX Aggregator** is a high-performance Python/FastAPI ETL system designed to ingest, normalize, and track price changes for millions of books from multiple sources (Yakaboo, Vivat). It uses a distributed architecture with Redis queues and a "Universal Worker" pattern.

## STRUCTURE
```
.
├── app/
│   ├── core/
│   │   ├── adapters/   # JSON configs mapping external APIs to internal schema
│   │   └── engine/     # The "Universal Worker" logic (ETL core)
│   └── classifiers/    # ISBN/Category classification logic
├── scripts/            # Spiders, service runners, and maintenance tools
├── prisma/             # Database schema (PostgreSQL) and migrations
├── data/               # Raw data dumps (JSONL) - mostly historical/reference
└── vendor/             # EXTERNAL CODE (OpenCode) - DO NOT MODIFY
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add Source** | `app/core/adapters/` | Create new JSON config |
| **ETL Logic** | `app/core/engine/worker.py` | The brain of the operation |
| **Spiders** | `scripts/*_spider.py` | Data fetching logic (Producer) |
| **Services** | `scripts/run_*_service.sh` | Infinite loop supervisors |
| **Schema** | `prisma/schema.prisma` | DB definition (modify here -> generate) |

## KEY COMPONENTS

### 1. Ingestion Engine (`app/core/engine/worker.py`)
- **Pattern**: Reliable Queue (Redis `BRPOPLPUSH`).
- **Feature**: Dynamic Adapter Loading. Loads all `*.json` from `adapters/` and dispatches based on `source` field.
- **Logic**: JSONPath extraction -> Deduplication (Redis Lock) -> Content Hash Check -> UPSERT.

### 2. Spiders (`scripts/`)
- **Yakaboo**: `yakaboo_spider.py` (Deep pagination via POST).
- **Vivat**: `vivat_spider.py` (JSONAPI with nested attributes).
- **Architecture**: Stateful (save offset to JSON), Backpressure-aware (pauses if queue > 50k).

## CONVENTIONS
- **Imports**: Absolute imports only (`from app.core import...`).
- **Async**: Everything is async (`aiohttp`, `redis.asyncio`).
- **DB Access**: STRICTLY via `Prisma` ORM. No raw `psycopg2` unless necessary for migrations.
- **JSONB**: We store FULL raw response in `products.raw_data` to allow future re-parsing without scraping.

## COMMANDS
```bash
# Install
pip install -r requirements.txt && prisma generate

# Run Spiders (Background Service)
nohup ./scripts/run_yakaboo_service.sh &
nohup ./scripts/run_vivat_service.sh &

# Run Workers (Universal)
# Runs indefinitely, pulling from ANY queue defined in adapters
python -m app.core.engine.worker --all-adapters
```

## ANTI-PATTERNS (THIS PROJECT)
- **NEVER** put parsing logic in Spiders. Spiders must be "dumb" fetchers. Parsing happens in Worker via Adapters.
- **NEVER** modify `vendor/` directory.
- **NEVER** commit secrets (`.env`).

## NOTES
- **DB Migration**: `isbn` and `sku` columns are `VARCHAR(64)` to handle long codes from some sources.
- **Queues**: `queue:yakaboo`, `queue:vivat`.
- **DLQ**: Failed tasks go to `queue:<source>:dlq`.
