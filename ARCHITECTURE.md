# ONIX Aggregator Architecture v1.0

This document outlines the technical architecture of the ONIX Aggregator system.

## 🌀 Overall System Flow
The system follows a distributed **Producer-Consumer** pattern using Redis as a reliable message broker.

```mermaid
graph LR
    subgraph Producers (Spiders)
        Y[Yakaboo Spider]
        V[Vivat Spider]
    end

    subgraph Broker
        R[(Redis Queues)]
    end

    subgraph Consumers
        W1[Universal Worker]
        W2[Universal Worker]
        W3[Universal Worker]
    end

    subgraph Storage
        P[(PostgreSQL)]
        PH[(Price History)]
    end

    Y -->|LPUSH queue:yakaboo| R
    V -->|LPUSH queue:vivat| R
    R -->|BRPOPLPUSH| W1
    R -->|BRPOPLPUSH| W2
    R -->|BRPOPLPUSH| W3
    W1 -->|Upsert| P
    W1 -->|Insert Delta| PH
```

## 🛠 Core Components

### 1. Multi-Source Spiders (`scripts/*_spider.py`)
- **Async Execution**: Built on `aiohttp` for high-concurrency network I/O.
- **Deep Pagination**: 
  - **Yakaboo**: Uses `search_after` cursor-based pagination to traverse 1M+ records without performance degradation.
  - **Vivat**: Uses `page[offset]` with JSONAPI includes.
- **State Persistence**: Progress is saved to `*_state.json` files after every successful batch.
- **Backpressure**: Spiders monitor the Redis queue depth and pause if it exceeds 50,000 tasks.

### 2. Universal Ingestion Engine (`app/core/engine/worker.py`)
- **Declarative Mapping**: Logic is decoupled from the source structure via JSON Adapters.
- **Enhanced Selectors**:
  - **Dot Notation**: Supports `attributes.product.label`.
  - **Array Filtering**: Can locate specific items in nested lists (e.g., finding the EAN/ISBN attribute in Vivat's complex response).
- **Idempotency**: Calculates a SHA256 `content_hash` of the normalized data. If the hash matches the database record, the update is skipped (updating only `updated_at`).

### 3. Reliable Queue Mechanism
- Uses Redis `BRPOPLPUSH` to move tasks from the main queue to a `processing` queue atomically.
- If a worker crashes, the task remains in the `processing` queue for recovery.
- Failed tasks after 3 retries are moved to a `DLQ` (Dead Letter Queue) for manual inspection.

## 🗄 Database Design
- **Single Product Table**: Both sources populate the same `products` table, distinguished by `source_name`.
- **VARCHAR(64)**: Global identifiers (ISBN/SKU) are expanded to handle long barcodes from various publishers.
- **JSONB Storage**: The original raw response from the source is stored in the `raw_data` column, allowing for future re-parsing without re-scraping.
- **Price History**: Trigger-like logic in the worker creates a new record in `price_history` only when the price value changes.

## 🚀 Scalability
- **Horizontal Scaling**: Simply start more worker processes to increase ingestion speed.
- **New Source Onboarding**: Requires only a new JSON adapter and a lightweight spider script. No changes to the core engine are needed.
