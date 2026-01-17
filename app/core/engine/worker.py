"""
Universal ETL Worker with Reliable Queue Pattern.

Fixes implemented:
- BRPOPLPUSH for atomic task processing (no task loss on crash)
- Dead Letter Queue (DLQ) with retry counter
- Distributed locks for deduplication
- Backpressure mechanism for fan-out
- Proper connection management
"""
import json
import hashlib
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = str(Path(__file__).resolve().parents[3])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from prisma import Prisma, Json
from redis.asyncio import Redis
from app.classifiers.isbn_classifier import classify_item


# ============================================================================
# CONFIGURATION
# ============================================================================

MAX_RETRIES = 3                    # Max retry attempts before DLQ
LOCK_TTL_SECONDS = 30              # Distributed lock expiration
MAX_QUEUE_DEPTH = 50000            # Backpressure threshold
CHUNK_SIZE = 1000                  # Batch size for fan-out
PROCESSING_TIMEOUT = 300           # Seconds before orphaned task recovery
BACKPRESSURE_WAIT_SECONDS = 5      # Wait time when queue is full


def clean_for_json(data: Any) -> Any:
    """Recursively converts types not supported by JSON (e.g., Decimal)."""
    if isinstance(data, dict):
        return {str(k): clean_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_for_json(i) for i in data]
    elif hasattr(data, "__str__") and "Decimal" in str(type(data)):
        return float(data)
    return data


# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("UniversalWorker")


class UniversalWorker:
    """
    Robust ETL worker with:
    - Reliable queue pattern (BRPOPLPUSH)
    - Dead Letter Queue for poison messages
    - Distributed locking for deduplication
    - Backpressure for controlled fan-out
    """
    
    def __init__(self, adapter_path: str, redis_url: str):
        self.adapter_config = self._load_adapter(adapter_path)
        self.redis_url = redis_url
        self.db = Prisma()
        self.redis: Optional[Redis] = None
        self.source_name = self.adapter_config["source_name"]
        
        # Queue names
        self.queue_name = f"queue:{self.source_name}"
        self.processing_queue = f"queue:{self.source_name}:processing"
        self.dlq_queue = f"queue:{self.source_name}:dlq"
        
        # Stats
        self._processed_count = 0
        self._error_count = 0
        self._dlq_count = 0

    def _load_adapter(self, path: str) -> Dict[str, Any]:
        with open(path, "r") as f:
            return json.load(f)

    async def connect(self):
        """Connect to Redis and Postgres."""
        await self.db.connect()
        self.redis = Redis.from_url(self.redis_url, decode_responses=True)
        logger.info(f"Worker connected to Redis ({self.redis_url}) and Postgres")

    async def disconnect(self):
        """Graceful shutdown."""
        if self.db.is_connected():
            await self.db.disconnect()
        if self.redis:
            await self.redis.aclose()
        logger.info(f"Worker shutdown. Processed: {self._processed_count}, Errors: {self._error_count}, DLQ: {self._dlq_count}")

    def _extract_value(self, data: Any, selector: Any) -> Any:
        """
        Extracts value using:
        1. String dot notation: "foo.bar" -> data["foo"]["bar"]
        2. List of keys (for keys with dots): ["foo", "bar.baz"] -> data["foo"]["bar.baz"]
        3. Dict configuration for array filtering.
        """
        if isinstance(selector, str):
            # Simple dot notation traversal
            current = data
            for part in selector.split('.'):
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    try:
                        current = current[int(part)]
                    except IndexError:
                        return None
                else:
                    return None
                
                if current is None:
                    return None
            return current

        elif isinstance(selector, list):
            # Exact path traversal (handling keys with dots)
            current = data
            for part in selector:
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and str(part).isdigit():
                    try:
                        current = current[int(part)]
                    except IndexError:
                        return None
                else:
                    return None
                
                if current is None:
                    return None
            return current

        elif isinstance(selector, dict):
            # Complex extraction with array filtering
            path = selector.get("path", "")
            filter_conf = selector.get("filter")
            extract_field = selector.get("extract")

            # Get the list to filter
            items = self._extract_value(data, path)
            if not isinstance(items, list):
                return None

            # Find matching item
            found = None
            if filter_conf:
                f_key = filter_conf.get("key")
                f_val = filter_conf.get("value")
                for item in items:
                    # Check if nested key matches value
                    val = self._extract_value(item, f_key)
                    if val == f_val:
                        found = item
                        break
            else:
                # No filter, take first item? Or just use 'items' if extract is not set?
                # If no filter, we assume we want to extract from the list itself or first item
                # But typically this structure implies filtering. 
                # Let's assume filter is optional and we just operate on list if not present,
                # but 'extract' would need to handle list. 
                # For simplicity, if no filter, take first item.
                if items:
                    found = items[0]

            if found and extract_field:
                return self._extract_value(found, extract_field)
            
            return found

        return None

    def _map_data(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Maps raw data using selectors from adapter config."""
        selectors = self.adapter_config["selectors"]
        mapped = {}
        for target_field, source_selector in selectors.items():
            mapped[target_field] = self._extract_value(raw_record, source_selector)
        return mapped

    # ========================================================================
    # RELIABLE QUEUE OPERATIONS
    # ========================================================================

    async def _pop_task_reliably(self) -> Optional[str]:
        """
        Atomically move task from main queue to processing queue.
        Returns task JSON string or None if queue is empty.
        Uses BRPOPLPUSH for atomic pop-and-push operation.
        """
        # BRPOPLPUSH atomically pops from source and pushes to destination
        # This ensures task is never lost even if worker crashes after pop
        result = await self.redis.brpoplpush(
            self.queue_name, 
            self.processing_queue, 
            timeout=5
        )
        return result

    async def _ack_task(self, task_json: str):
        """Remove successfully processed task from processing queue."""
        await self.redis.lrem(self.processing_queue, 1, task_json)

    async def _move_to_dlq(self, task_json: str, error: str):
        """Move failed task to Dead Letter Queue with error info."""
        try:
            task = json.loads(task_json)
            task["_dlq_error"] = str(error)[:500]  # Truncate error message
            task["_dlq_timestamp"] = datetime.now(timezone.utc).isoformat()
            await self.redis.lpush(self.dlq_queue, json.dumps(task))
            await self.redis.lrem(self.processing_queue, 1, task_json)
            self._dlq_count += 1
            logger.warning(f"Task moved to DLQ: {error[:100]}")
        except Exception as e:
            logger.error(f"Failed to move task to DLQ: {e}")

    async def _requeue_with_retry(self, task_json: str, error: str):
        """Requeue task with incremented retry counter."""
        try:
            task = json.loads(task_json)
            retry_count = task.get("_retry_count", 0)
            
            if retry_count >= MAX_RETRIES:
                await self._move_to_dlq(task_json, f"Max retries ({MAX_RETRIES}) exceeded: {error}")
            else:
                task["_retry_count"] = retry_count + 1
                task["_last_error"] = str(error)[:200]
                await self.redis.lpush(self.queue_name, json.dumps(task))
                await self.redis.lrem(self.processing_queue, 1, task_json)
                logger.info(f"Task requeued (retry {retry_count + 1}/{MAX_RETRIES})")
        except Exception as e:
            logger.error(f"Failed to requeue task: {e}")

    # ========================================================================
    # DISTRIBUTED LOCKING
    # ========================================================================

    async def _acquire_lock(self, key: str) -> bool:
        """
        Try to acquire a distributed lock.
        Returns True if lock acquired, False if already locked.
        """
        lock_key = f"lock:{self.source_name}:{key}"
        acquired = await self.redis.set(lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS)
        return acquired is not None

    async def _release_lock(self, key: str):
        """Release distributed lock."""
        lock_key = f"lock:{self.source_name}:{key}"
        await self.redis.delete(lock_key)

    # ========================================================================
    # BACKPRESSURE
    # ========================================================================

    async def _wait_for_backpressure(self):
        """Wait if queue is too deep (backpressure mechanism)."""
        while True:
            queue_depth = await self.redis.llen(self.queue_name)
            if queue_depth < MAX_QUEUE_DEPTH:
                return
            logger.info(f"Backpressure: queue depth {queue_depth} > {MAX_QUEUE_DEPTH}, waiting...")
            await asyncio.sleep(BACKPRESSURE_WAIT_SECONDS)

    # ========================================================================
    # TASK PROCESSING
    # ========================================================================

    async def process_task(self, task: Dict[str, Any], task_json: str):
        """Main task processing logic with proper error handling."""
        task_type = task.get("type")

        try:
            if task_type == "data_row":
                await self._handle_data_row(task.get("payload"))
            elif task_type == "file_bulk":
                await self._handle_file_bulk(task)
            else:
                logger.warning(f"Unknown task type: {task_type}")
            
            # Success - acknowledge task
            await self._ack_task(task_json)
            self._processed_count += 1
            
        except Exception as e:
            self._error_count += 1
            error_msg = str(e)
            
            # Check if it's a transient error (DB connection, etc.)
            if "Can't reach database" in error_msg or "connection" in error_msg.lower():
                logger.warning(f"Transient error, will retry: {error_msg}")
                await self._requeue_with_retry(task_json, error_msg)
                await asyncio.sleep(5)  # Brief pause for recovery
            else:
                # Permanent error - retry with counter
                await self._requeue_with_retry(task_json, error_msg)

    async def _handle_file_bulk(self, task: Dict[str, Any]):
        """
        Fan-out: Read large file and create micro-tasks.
        Uses chunked enqueueing with backpressure.
        """
        file_path = task.get("target")
        logger.info(f"🚀 Fan-out started for file: {file_path}")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        count = 0
        chunk = []
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    payload = json.loads(line.strip())
                    micro_task = {
                        "type": "data_row",
                        "source": self.source_name,
                        "payload": payload,
                    }
                    chunk.append(json.dumps(micro_task))
                    count += 1

                    # Push in chunks with backpressure
                    if len(chunk) >= CHUNK_SIZE:
                        await self._wait_for_backpressure()
                        
                        # Use pipeline for efficiency
                        async with self.redis.pipeline() as pipe:
                            for task_json in chunk:
                                pipe.lpush(self.queue_name, task_json)
                            await pipe.execute()
                        
                        chunk.clear()
                        
                        if count % 10000 == 0:
                            logger.info(f"Queued {count} rows from {path.name}...")
                            
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in line: {e}")
                except Exception as e:
                    logger.error(f"Error parsing line: {e}")

        # Push remaining chunk
        if chunk:
            await self._wait_for_backpressure()
            async with self.redis.pipeline() as pipe:
                for task_json in chunk:
                    pipe.lpush(self.queue_name, task_json)
                await pipe.execute()

        logger.info(f"✅ Fan-out complete. Total tasks created: {count}")

    async def _handle_data_row(self, raw_payload: Dict[str, Any]):
        """
        Process single data row with distributed lock for deduplication.
        """
        if not raw_payload:
            raise ValueError("Empty payload")
            
        mapped = self._map_data(raw_payload)
        ext_id = str(mapped.get("external_id") or "")
        
        if not ext_id:
            raise ValueError("Missing external_id")

        # Acquire distributed lock to prevent race conditions
        if not await self._acquire_lock(ext_id):
            logger.debug(f"Skipping (locked by another worker): {ext_id}")
            return

        try:
            barcode = str(mapped.get("isbn") or "")
            classification = classify_item(barcode)

            clean_payload = clean_for_json(raw_payload)
            content_str = json.dumps(clean_payload, sort_keys=True)
            new_hash = hashlib.sha256(content_str.encode()).hexdigest()

            new_price = mapped.get("price")
            if new_price is not None:
                new_price = float(new_price)

            # UPSERT with hash-based change detection
            result = await self.db.query_raw(
                """
                INSERT INTO public.products 
                (id, source_name, external_id, sku, isbn, title, price, raw_data, content_hash, created_at, updated_at)
                VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7::jsonb, $8, NOW(), NOW())
                ON CONFLICT (source_name, external_id) 
                DO UPDATE SET 
                    price = EXCLUDED.price,
                    raw_data = EXCLUDED.raw_data,
                    content_hash = EXCLUDED.content_hash,
                    updated_at = NOW()
                WHERE products.content_hash != EXCLUDED.content_hash
                RETURNING id::text, price::float as new_price;
                """,
                self.source_name,
                ext_id,
                mapped.get("sku"),
                classification.code,
                mapped.get("title") or "Untitled",
                new_price,
                json.dumps(clean_payload),
                new_hash,
            )

            if result:
                row = result[0]
                p_id = row.get("id")
                n_p = row.get("new_price")

                if n_p is not None and p_id:
                    await self.db.pricehistory.create(
                        data={"productId": p_id, "price": n_p}
                    )

        finally:
            # Always release lock
            await self._release_lock(ext_id)

    # ========================================================================
    # RECOVERY
    # ========================================================================

    async def recover_orphaned_tasks(self):
        """
        Move orphaned tasks from processing queue back to main queue.
        Should be called on startup or periodically.
        """
        count = 0
        while True:
            task_json = await self.redis.rpoplpush(self.processing_queue, self.queue_name)
            if not task_json:
                break
            count += 1
        
        if count > 0:
            logger.info(f"🔄 Recovered {count} orphaned tasks from processing queue")
        return count

    # ========================================================================
    # MAIN LOOP
    # ========================================================================

    async def run(self):
        """Main worker loop with reliable queue processing."""
        await self.connect()
        
        # Recover any orphaned tasks from previous crash
        await self.recover_orphaned_tasks()
        
        logger.info(f"Worker [{self.source_name}] active. Queue: {self.queue_name}")
        logger.info(f"Config: MAX_RETRIES={MAX_RETRIES}, MAX_QUEUE_DEPTH={MAX_QUEUE_DEPTH}")

        try:
            while True:
                task_json = await self._pop_task_reliably()
                if task_json:
                    try:
                        task = json.loads(task_json)
                        await self.process_task(task, task_json)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in task: {e}")
                        await self._move_to_dlq(task_json, f"Invalid JSON: {e}")
                        
        except asyncio.CancelledError:
            logger.info("Shutdown signal received...")
        finally:
            await self.disconnect()

    # ========================================================================
    # MONITORING
    # ========================================================================

    async def get_stats(self) -> Dict[str, int]:
        """Get current queue statistics."""
        return {
            "queue_depth": await self.redis.llen(self.queue_name),
            "processing": await self.redis.llen(self.processing_queue),
            "dlq": await self.redis.llen(self.dlq_queue),
            "processed": self._processed_count,
            "errors": self._error_count,
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Universal ETL Worker")
    parser.add_argument("--adapter", required=True, help="Path to adapter JSON")
    parser.add_argument("--redis", default="redis://localhost:6379/0", help="Redis URL")
    parser.add_argument("--recover-only", action="store_true", help="Only recover orphaned tasks and exit")
    args = parser.parse_args()

    worker = UniversalWorker(args.adapter, args.redis)
    
    if args.recover_only:
        async def recover():
            await worker.connect()
            count = await worker.recover_orphaned_tasks()
            await worker.disconnect()
            print(f"Recovered {count} tasks")
        asyncio.run(recover())
    else:
        asyncio.run(worker.run())
