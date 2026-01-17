# Work Plan: Yakaboo API Spider Implementation

## Objective
Implement a high-performance, resilient spider to crawl the Yakaboo API and feed the ingestion queue for real-time updates.

## Technical Requirements
- **Language**: Python 3.12
- **Library**: `aiohttp` for async networking.
- **Queue**: Redis (using `redis.asyncio`).
- **Target API**: `https://api2.yakaboo.ua/api/catalog/vue_storefront_catalog_1/product/_search`

## Architecture
The spider operates as a **Producer** in the ETL pipeline.
`Spider` -> `Redis Queue (queue:yakaboo)` -> `UniversalWorker` -> `PostgreSQL`

## Step-by-Step Implementation

### 1. Create `scripts/yakaboo_spider.py`
- [ ] Implement `YakabooSpider` class.
- [ ] **Method: `fetch_page`**: Performs POST request with `search_after` and `size=100`.
- [ ] **Method: `push_to_redis`**: Batch pushes results to `queue:yakaboo`.
- [ ] **Method: `monitor_backpressure`**: Polls Redis queue depth; pauses if > 50,000.
- [ ] **State Handling**: Save `search_after` values to `yakaboo_state.json` after every successful batch.

### 2. Payload Mapping
The spider MUST wrap the API response source into the following format:
```json
{
  "type": "data_row",
  "source": "yakaboo",
  "payload": <raw_api_response_object>
}
```

### 3. CLI Interface
- [ ] `--resume`: Start from the last saved state.
- [ ] `--limit`: Stop after N products.
- [ ] `--batch-size`: Number of products per API request (max 100).

## Verification Plan
1. **Dry Run**: Log the first 10 products without pushing to Redis.
2. **Integration Test**:
   - Start 1 Worker: `python -m app.core.engine.worker --adapter app/core/adapters/yakaboo.json`
   - Start Spider: `python scripts/yakaboo_spider.py --limit 500`
   - Verify DB: `SELECT count(*) FROM products WHERE updated_at > NOW() - INTERVAL '5 minutes';`
3. **Backpressure Test**: Manually fill Redis and verify spider pauses.

## Important Notes
- **Deduplication**: Handled by `UniversalWorker` via `content_hash`. The spider just needs to send data.
- **User Request**: Do NOT scan local files. Only use the API.
