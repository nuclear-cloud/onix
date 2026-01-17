# SCRIPTS & AUTOMATION AGENTS

## OVERVIEW
This directory contains the operational layer for the ONIX Aggregator. These scripts handle the full lifecycle of data: from initial scraping (Spiders) to queue management (Monitoring) and system maintenance.

## CATALOG
### 1. Spiders (Producers)
- `yakaboo_spider.py`: High-volume scraper using POST-based pagination.
- `vivat_spider.py`: Efficient JSONAPI fetcher for the Vivat book catalog.
- `enqueue_task.py`: Utility to manually inject tasks into the processing pipeline.

### 2. Supervisors & Services
- `run_vivat_service.sh`: Shell supervisor that ensures the Vivat spider runs indefinitely with 1-hour intervals.
- `run_yakaboo_import.sh`: Managed import process for Yakaboo datasets.
- `run_spider_service.sh`: Generic wrapper for background spider execution.

### 3. Monitoring & DLQ
- `queue_monitor.py`: Critical tool for Redis health. Supports `status`, `dlq-list`, `dlq-retry`, and `recover`.
- `etl_monitor.sh`: Real-time dashboard showing DB record counts and ingestion status.
- `check_redis.py`: Rapid connectivity check for the cache layer.

### 4. Maintenance & Schema
- `debug_db.py`: Verifies Prisma ORM connectivity and PostgreSQL state.
- `flush_redis.py`: emergency purge of all processing queues.
- `analyze_yakaboo_schema.py`: Research tool for mapping external fields to internal ONIX schema.

## HOW TO RUN
### Monitoring Progress
To check the health of the ingestion pipeline:
```bash
# View Redis queue lengths and DLQ status
python scripts/queue_monitor.py status --source vivat

# Check DB record distribution
./scripts/etl_monitor.sh
```

### Manual Intervention
If tasks are stuck in the Dead Letter Queue:
```bash
# Move failed tasks back to the main queue
python scripts/queue_monitor.py dlq-retry --source yakaboo
```

## AUTOMATION
### Systemd Integration
In production, spiders are managed via systemd units found in this directory:
- `yakaboo-spider.service`
- `vivat-spider.service`

**Management Commands:**
```bash
sudo cp scripts/*.service /etc/systemd/system/
sudo systemctl enable vivat-spider
sudo systemctl start vivat-spider
```

### Recovery Logic
The `.sh` supervisors implement a "Self-Healing" loop:
- **On Success**: Sleep 1 hour (periodic refresh).
- **On Crash**: Sleep 1 minute (backoff) and resume from the last saved state.
