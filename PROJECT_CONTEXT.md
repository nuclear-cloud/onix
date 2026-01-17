# PROJECT CONTEXT - ONIX Aggregator v1.0

**Current Status:** Production Ready - v1.0 Stable  
**Ingestion Progress:** Multi-source (Yakaboo ~1M, Vivat ~26k)  
**Last Major Update:** 2026-01-17 (Vivat Integration & Universal Worker Upgrade)

---

## 🏗 High-Level Architecture
The project uses a high-performance **Distributed Queue** architecture designed for high throughput and reliable data normalization.

### 1. Data Flow
`Spiders (Yakaboo/Vivat)` ──▶ `Redis (Named Queues)` ──▶ `Universal Workers` ──▶ `PostgreSQL (JSONB + Delta)`

### 2. Universal Worker Engine
The heart of the system is the `UniversalWorker` (`app/core/engine/worker.py`), which features:
- **Declarative Mapping**: Uses JSON adapters to handle nested structures and dot-notation keys.
- **Deep Array Filtering**: Extracts specific values (like ISBN) from complex nested lists via smart filters.
- **Deduplication**: SHA256 hashing ensures only changed data triggers a DB write.
- **Price Delta Tracking**: Maintains an audit trail of price changes in `price_history`.

---

## 🛠 Tech Stack
- **Backend:** Python 3.12 (Aiohttp, Redis-py)
- **Database:** PostgreSQL 16 (Managed via Prisma ORM)
- **Infrastructure:** Redis 7 (AOF enabled), Docker Compose
- **Monitoring:** Custom shell supervisors and Python-based queue monitors.

---

## 📂 Key Entry Points
- `app/core/engine/worker.py`: Ingestion logic.
- `app/core/adapters/`: Source-specific configurations.
- `scripts/run_*_service.sh`: Daemon supervisors for spiders.
- `prisma/schema.prisma`: Single source of truth for the data model.

---

## 📅 Roadmap 2026
1. [x] Distributed Worker Architecture.
2. [x] Multi-source Integration (Yakaboo + Vivat).
3. [x] Universal Mapping Engine (JSONPath-like).
4. [x] Database Optimization (VARCHAR 64 for identifiers).
5. [Next] API Layer implementation for frontend consumers.
6. [Next] AI Enrichment (Summaries, Keywords).
