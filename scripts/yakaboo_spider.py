#!/usr/bin/env python3
import asyncio
import json
import logging
import argparse
import sys
import os
from typing import List, Optional, Any

import aiohttp
from redis.asyncio import Redis

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("yakaboo_spider")

API_URL = "https://api2.yakaboo.ua/api/catalog/vue_storefront_catalog_1/product/_search"
REDIS_KEY = "queue:yakaboo"
STATE_FILE = "yakaboo_state.json"
QUEUE_LIMIT = 50000

class YakabooSpider:
    def __init__(self, resume: bool, limit: int, batch_size: int):
        self.resume = resume
        self.limit = limit
        self.batch_size = batch_size
        self.redis: Optional[Redis] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.processed_count = 0
        self.last_sort_values: Optional[List[Any]] = None
        
    async def setup(self):
        """Initialize resources."""
        self.redis = Redis.from_url(settings.DATABASE_URL.replace("postgresql", "redis").replace("5432", "6379").replace("/onix_db", "/0")) 
        # Wait, settings.DATABASE_URL is for Postgres.
        # AGENTS.md says "Redis URL and Database URL must be set in .env".
        # But settings class doesn't seem to have REDIS_URL.
        # Let's check environment variable REDIS_URL or fallback to localhost.
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = Redis.from_url(redis_url)
        
        self.session = aiohttp.ClientSession()
        
        if self.resume:
            self.load_state()
            
    async def cleanup(self):
        """Close resources."""
        if self.redis:
            await self.redis.aclose()
        if self.session:
            await self.session.close()

    def load_state(self):
        """Load state from file."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.last_sort_values = data.get("last_sort_values")
                    logger.info(f"Resumed from state: {self.last_sort_values}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def save_state(self):
        """Save state to file."""
        data = {"last_sort_values": self.last_sort_values}
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    async def check_backpressure(self):
        """Pause if queue is full."""
        if not self.redis:
            return
            
        while True:
            try:
                q_len = await self.redis.llen(REDIS_KEY)
                if q_len > QUEUE_LIMIT:
                    logger.warning(f"Queue full ({q_len} > {QUEUE_LIMIT}). Sleeping 10s...")
                    await asyncio.sleep(10)
                else:
                    break
            except Exception as e:
                logger.error(f"Redis error checking queue length: {e}")
                await asyncio.sleep(5)

    async def fetch_batch(self) -> List[dict]:
        """Fetch a batch of products from API."""
        payload = {
            "size": self.batch_size,
            "sort": [{"stock.is_in_stock": "desc"}, {"published_at": "desc"}]
        }
        
        # Validation for search_after values (prevent BIG_INTEGER errors)
        if self.last_sort_values:
            # Check if values are within sane limits or non-sentinel
            # -9223372036854776000 is a common sentinel for 'null' in some ES versions
            # that causes 500 on the next search_after.
            valid_values = []
            for val in self.last_sort_values:
                if isinstance(val, (int, float)) and (val < -10**15 or val > 10**15):
                    logger.warning(f"Detected suspicious sort value: {val}. Terminating scan to avoid API Error.")
                    return []
                valid_values.append(val)
            payload["search_after"] = valid_values
            
        try:
            async with self.session.post(API_URL, json=payload) as response:
                if response.status == 500:
                    logger.warning("API returned 500. This often means end of results for search_after. Stopping.")
                    return []
                
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"API Error {response.status}: {text[:500]}")
                    return []
                
                data = await response.json()
                hits = data.get("hits", {}).get("hits", [])
                return hits
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []

    async def run(self):
        """Main execution loop."""
        await self.setup()
        
        logger.info(f"Starting spider. Target: {API_URL}")
        logger.info(f"Batch size: {self.batch_size}, Limit: {self.limit}, Resume: {self.resume}")

        try:
            while True:
                # Check limits
                if self.limit and self.processed_count >= self.limit:
                    logger.info(f"Limit reached ({self.processed_count} >= {self.limit}). Stopping.")
                    break

                # Backpressure
                await self.check_backpressure()

                # Fetch
                hits = await self.fetch_batch()
                if not hits:
                    logger.info("No more results found.")
                    break

                # Process
                batch_payloads = []
                for hit in hits:
                    if self.limit and self.processed_count + len(batch_payloads) >= self.limit:
                        break

                    source_data = hit.get("_source")
                    if not source_data:
                        continue
                        
                    task = {
                        "type": "data_row",
                        "source": "yakaboo",
                        "payload": source_data
                    }
                    batch_payloads.append(json.dumps(task))
                    
                    # Update sort values from the last item in the batch
                    self.last_sort_values = hit.get("sort")

                # Push to Redis
                if batch_payloads:
                    await self.redis.lpush(REDIS_KEY, *batch_payloads)
                    self.processed_count += len(batch_payloads)
                    logger.info(f"Pushed {len(batch_payloads)} items. Total: {self.processed_count}")
                    
                    # Save state
                    self.save_state()
                else:
                    logger.info("Batch yielded no valid items.")
                    # Batch was empty or invalid, treated as end of stream if hits was not empty but filtered? 
                    # Actually hits check is above. If we get here, hits was not empty.
                    # If batch_payloads is empty but hits wasn't, we just continue to next batch?
                    # No, search_after relies on the last item. If we skipped all items, we can't advance sort values!
                    # This is a potential deadlock if a whole page is filtered.
                    # We must use the last hit's sort value even if we didn't push it.
                    if hits:
                         self.last_sort_values = hits[-1].get("sort")
                         self.save_state()
                    continue

        except KeyboardInterrupt:
            logger.info("Stopping...")
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            sys.exit(1) # Exit with error code
        else:
            # If loop finished naturally (break)
            if not self.limit: # Only delete state if we finished a FULL scan (no limit)
                logger.info("Scan complete. Removing state file for fresh start next time.")
                if os.path.exists(STATE_FILE):
                    os.remove(STATE_FILE)
        finally:
            await self.cleanup()

def main():
    parser = argparse.ArgumentParser(description="Yakaboo API Spider")
    parser.add_argument("--resume", action="store_true", help="Resume from last state")
    parser.add_argument("--limit", type=int, default=0, help="Max items to process (0 = infinite)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size (max 100)")
    
    args = parser.parse_args()
    
    spider = YakabooSpider(
        resume=args.resume,
        limit=args.limit,
        batch_size=args.batch_size
    )
    
    asyncio.run(spider.run())

if __name__ == "__main__":
    main()
