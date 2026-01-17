# ONIX Aggregator v1.0 (Universal Ingestion Engine)

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/redis-7-red.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://www.docker.com/)

**High-performance distributed ingestion engine for the Ukrainian book market.**

This system handles millions of metadata records using a resilient queue-based architecture, featuring real-time price tracking and source-agnostic normalization.

## 🏗 Architecture 1.0
- **Multi-Source Spiders**: Resilient async crawlers for Yakaboo (API) and Vivat (JSONAPI).
- **Universal Ingestion Engine**: A single worker logic that handles diverse data structures via JSON adapters.
- **Reliable Queue (Redis)**: Uses `BRPOPLPUSH` to guarantee zero data loss during ingestion.
- **Delta Price Tracking**: Records price history only on actual changes using SHA256 content hashing.
- **Auto-Scaling**: Modular design allows running multiple workers across different sources concurrently.

## 🚀 Quick Start

### 1. Infrastructure
```bash
docker-compose up -d
```

### 2. Environment
```bash
pip install -r requirements.txt
prisma generate
```

### 3. Run Ingestion Services
```bash
# Start Yakaboo Spider Service
nohup ./scripts/run_spider_service.sh &

# Start Vivat Spider Service
nohup ./scripts/run_vivat_service.sh &

# Start Universal Workers
# For Yakaboo:
python -m app.core.engine.worker --adapter app/core/adapters/yakaboo.json
# For Vivat:
python -m app.core.engine.worker --adapter app/core/adapters/vivat.json
```

## 📊 Operations & Monitoring
- **Queue Health**: `python scripts/queue_monitor.py status`
- **DB Stats**: `docker exec onix_postgres_prod psql -U onix_user -d onix_db -c "SELECT source_name, count(*) FROM products GROUP BY source_name;"`
- **Logs**: Centralized logs in `logs/` directory and service-specific logs (e.g., `vivat_service.log`).

## 📂 Project Structure
```
onix_project/
├── app/
│   ├── core/
│   │   ├── adapters/     # Declarative Mapping (JSON)
│   │   └── engine/       # Universal Worker logic
│   └── classifiers/      # Data sanitization (ISBN/EAN)
├── scripts/              # Spiders, Supervisors & Maintenance
├── prisma/               # Database Schema & Migrations
└── data/                 # Raw datasets (historical)
```


### 2. Environment
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Ingestion
```bash
export PYTHONPATH=$(pwd)
# Start 5 workers in background
for i in {1..5}; do ./venv/bin/python -m app.core.engine.worker --adapter app/core/adapters/yakaboo.json >> worker.log 2>&1 & done

# Enqueue a file
./venv/bin/python scripts/enqueue_task.py --file data/yakaboo_complete_final.jsonl
```

## 📊 Operations & Monitoring
- **Web UI**: Access OpenCode at `http://localhost:3000`
- **Queue Stats**: `./venv/bin/python scripts/check_redis.py`
- **DB Stats**: `docker exec onix_postgres_prod psql -U onix_user -d onix_db -c "SELECT count(*) FROM products;"`

## 📂 Structure
```
onix_project/
├── app/
│   ├── core/
│   │   ├── adapters/     # JSON Mapping configs
│   │   └── engine/       # Distributed Worker logic
│   └── classifiers/      # ISBN/EAN brain
├── scripts/              # Ops and Debug scripts
├── prisma/               # Schema and DB models
└── docker-compose.yml    # Infrastructure
```
