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
    
    # Run loop
    while True:
        try:
            print(f"[Worker] Starting monitoring cycle at {datetime.now()}...")
            
            async with AsyncSessionLocal() as db:
                # 1. Initialize Monitor with DB persistence
                monitor = MonitorService(db=db)
                print("[Worker] Loading persistent state from database...")
                await monitor.initialize_state()
                
                # 2. Check for changes
                changes = await monitor.check_for_changes()
                
                if not changes:
                    print("[Worker] No changes found since last check.")
                else:
                    print(f"[Worker] Detected {len(changes)} changes. Processing...")
                    
                    product_service = ProductService(db)
                    transformer = VivatTransformer()
                    
                    for change in changes:
                        url = change.url
                        print(f"  - Processing: {url}")
                        
                        try:
                            # 3. Scrape & Hash
                            scraped, content_hash = await monitor.scrape_and_hash(url)
                            
                            # 4. Transform
                            product_create = transformer.transform(scraped)
                            author_names = transformer.extract_authors(scraped.raw_json)
                            
                            # 5. Ingest to DB
                            db_product = await product_service.ingest_product(product_create, author_names)
                            
                            if db_product:
                                print(f"    - SUCCESS: Saved '{db_product.title}' (ISBN: {db_product.isbn_13})")
                            else:
                                print(f"    - SKIPPED: Already exists or no data changes.")
                                
                        except Exception as e:
                            print(f"    - ERROR processing {url}: {e}")
                
                # 6. Save State (Update last check time)
                print("[Worker] Saving cycle completion state...")
                await monitor.save_last_check()
                
        except Exception as e:
            print(f"[Worker] CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait before next cycle (e.g., 1 hour)
        SLEEP_SECONDS = 3600 
        print(f"[Worker] Monitoring cycle complete. Sleeping for {SLEEP_SECONDS} seconds...")
        await asyncio.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("[Worker] Stopped by user.")
