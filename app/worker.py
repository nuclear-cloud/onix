"""
Concept: Background Worker

This is the long-running process that periodically monitors the target website
for new or updated products. It integrates the Monitor, Scraper, Transformer,
and Product Service to automatically ingest data into the database.
"""

import asyncio
import sys
import os
from datetime import datetime

# Ensure app modules are importable
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.scraper.monitor_service import MonitorService
from app.services.product_service import ProductService
from app.scraper.transformer import VivatTransformer

async def run_worker():
    print("[Worker] Starting ONIX Scraper Background Worker...")
    
    # Initialize Monitor (keeps state in memory for now)
    # TODO: Load known state from DB to persist across restarts
    monitor = MonitorService()
    
    # Run loop
    while True:
        try:
            print(f"[Worker] Checking for updates at {datetime.now()}...")
            
            # 1. Check for changes
            changes = await monitor.check_for_changes()
            
            if not changes:
                print("[Worker] No changes found.")
            else:
                print(f"[Worker] Found {len(changes)} changes. Processing...")
                
                async with AsyncSessionLocal() as db:
                    product_service = ProductService(db)
                    transformer = VivatTransformer()
                    
                    for change in changes:
                        url = change.url
                        print(f"  - Processing: {url}")
                        
                        try:
                            # 2. Scrape & Hash
                            scraped, content_hash = await monitor.scrape_and_hash(url)
                            
                            # 3. Transform
                            product_create = transformer.transform(scraped)
                            author_names = transformer.extract_authors(scraped.raw_json)
                            
                            # 4. Ingest to DB
                            db_product = await product_service.ingest_product(product_create, author_names)
                            
                            if db_product:
                                print(f"    - SUCCESS: Saved '{db_product.title}' (ISBN: {db_product.isbn_13})")
                                # 5. Update Monitor State
                                monitor.update_known_state(url, content_hash)
                            else:
                                print(f"    - SKIPPED: Already exists or failed.")
                                # Still update state so we don't try again immediately?
                                # Yes, otherwise we loop forever on existing products.
                                monitor.update_known_state(url, content_hash)
                                
                        except Exception as e:
                            print(f"    - ERROR processing {url}: {e}")
                            
        except Exception as e:
            print(f"[Worker] CRITICAL ERROR: {e}")
        
        # Wait before next cycle (e.g., 1 hour)
        # For demo purposes, we can set this shorter, or configurable.
        # Let's say 1 hour + jitter? Or just 1 hour.
        SLEEP_SECONDS = 3600 
        print(f"[Worker] Sleeping for {SLEEP_SECONDS} seconds...")
        await asyncio.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("[Worker] Stopped by user.")
