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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("vivat_spider")

API_URL = "https://vivat.com.ua/jsonapi/product"
REDIS_KEY = "queue:vivat"
STATE_FILE = "vivat_state.json"
QUEUE_LIMIT = 50000
BATCH_SIZE = 50

class VivatSpider:
    def __init__(self, resume: bool, limit: int):
        self.resume = resume
        self.limit = limit
        self.redis: Optional[Redis] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.processed_count = 0
        self.current_offset = 0
        
    async def setup(self):
        """Initialize resources."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = Redis.from_url(redis_url)
        
        # User-Agent is crucial for Vivat
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        
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
                    self.current_offset = data.get("offset", 0)
                    logger.info(f"Resumed from offset: {self.current_offset}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def save_state(self):
        """Save state to file."""
        data = {"offset": self.current_offset}
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
        params = {
            "page[limit]": BATCH_SIZE,
            "page[offset]": self.current_offset,
            "include": "price,attribute"
        }
        
        try:
            async with self.session.get(API_URL, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"API Error {response.status}: {text[:200]}")
                    return []
                
                data = await response.json()
                items = data.get("data", [])
                return items
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []

    async def run(self):
        """Main execution loop."""
        await self.setup()
        
        logger.info(f"Starting Vivat spider. Target: {API_URL}")
        logger.info(f"Limit: {self.limit}, Resume: {self.resume}, Offset: {self.current_offset}")

        try:
            while True:
                # Check limits
                if self.limit and self.processed_count >= self.limit:
                    logger.info(f"Limit reached ({self.processed_count} >= {self.limit}). Stopping.")
                    break

                # Backpressure
                await self.check_backpressure()

                # Fetch
                items = await self.fetch_batch()
                if not items:
                    logger.info("No more items found or empty batch.")
                    # If empty, we assume end of list? Or check meta.total?
                    # Vivat returns empty data array when out of bounds.
                    break

                # Process
                batch_payloads = []
                for item in items:
                    if self.limit and self.processed_count + len(batch_payloads) >= self.limit:
                        break
                    
                    # We push the raw item. The Worker will extract fields using the adapter.
                    task = {
                        "type": "data_row",
                        "source": "vivat",
                        "payload": item
                    }
                    batch_payloads.append(json.dumps(task))

                # Push to Redis
                if batch_payloads:
                    await self.redis.lpush(REDIS_KEY, *batch_payloads)
                    count = len(batch_payloads)
                    self.processed_count += count
                    self.current_offset += BATCH_SIZE # Advance offset
                    
                    logger.info(f"Pushed {count} items. Total: {self.processed_count}. Next Offset: {self.current_offset}")
                    
                    # Save state
                    self.save_state()
                else:
                    break

        except KeyboardInterrupt:
            logger.info("Stopping...")
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            sys.exit(1)
        else:
            # If loop finished naturally
            if not self.limit:
                logger.info("Scan complete. Removing state file.")
                if os.path.exists(STATE_FILE):
                    os.remove(STATE_FILE)
        finally:
            await self.cleanup()

def main():
    parser = argparse.ArgumentParser(description="Vivat API Spider")
    parser.add_argument("--resume", action="store_true", help="Resume from last state")
    parser.add_argument("--limit", type=int, default=0, help="Max items to process (0 = infinite)")
    
    args = parser.parse_args()
    
    spider = VivatSpider(
        resume=args.resume,
        limit=args.limit
    )
    
    asyncio.run(spider.run())

if __name__ == "__main__":
    main()
