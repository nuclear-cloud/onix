# DEVELOPMENT PLAN 2026: Distributed ONIX Aggregator

**Status:** Implementation Active (Phase 1 Complete)  
**Senior Lead:** Antigravity AI  
**Focus:** Scalability, Resilience, Cost-Efficiency

---

## 1. Core Principles
- **Scalability**: Decoupled ingestion via Redis Queue (Producer/Worker pattern). [✅ IMPLEMENTED]
- **Resilience**: Redis AOF for queue persistence + SHA256 Fingerprinting for data integrity. [✅ IMPLEMENTED]
- **Flexibility**: Universal Workers driven by JSON Adapter Configurations. [✅ IMPLEMENTED]
- **Cost Efficiency**: Maximum utilization of Oracle ARM cores via multi-threaded asynchronous workers. [✅ IMPLEMENTED]

---

## 2. Infrastructure Isolation (Dev vs Prod)
Physical isolation via Docker ensures that experimental scrapers never pollute production data. [✅ DEPLOYED]

| Environment | PostgreSQL Port | Redis Port | Volume Path | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **PROD** | 5432 | 6379 | `./data/postgres_prod_data` | "Golden" records. |
| **DEV** | 5433 | 6380 | `./data/postgres_dev_data` | Sandbox. |

---

## 3. Data Schema (Hybrid Data Lake)
We use PostgreSQL with **Prisma ORM** and **pgvector**. [✅ SYNCED]

### `Product` (Table: `products`)
- `id`: UUID Primary Key.
- `sku` / `isbn`: Strict identifiers (ISBN validated via `ISBNClassifier`).
- `title` / `price`: Core SQL fields for fast filtering and sorting.
- `raw_data`: Full JSONB dump of source data (Data Lake pattern).
- `content_hash`: SHA256 of `raw_data` to prevent redundant updates.

### `PriceHistory` (Table: `price_history`)
- Records only **price deltas**. [✅ TESTED & WORKING]

---

## 4. Redis Task Manifest
Queue items are structured JSON objects: [✅ STANDARDIZED]
```json
{
  "type": "file_bulk",    // types: html, api, file_bulk, data_row, file_content
  "source": "yakaboo",
  "target": "path/to/data.jsonl"
}
```

---

## 5. Architectural Workflow ("The Grinder")

### Scenario A: Site Crawler / API [PENDING]
1. **Generator**: Scans URLs -> Pushes `type: html` task.

### Scenario B: Bulk File Fan-out (The 9GB Strategy) [✅ IMPLEMENTED]
1. **Master Worker**: Reads file line-by-line -> Pushes `type: data_row` tasks.
2. **Slave Workers**: Distributed processing of `data_row` -> DB.

---

## 📅 Roadmap 2026
1. [x] **Docker Compose**: Setup Redis AOF + Postgres + Qdrant.
2. [x] **Universal Worker**: Core engine implementation with JSON mapping.
3. [x] **Fan-out Logic**: Implementing the Master Worker for huge JSONL/CSV files.
4. [ ] **Crawler Logic**: Implement recursive URL scraper.
5. [ ] **RAG Integration**: Vectorization pipeline (pgvector).
