"""
Concept: Change Detection Demonstration

This script demonstrates how the system detects changes on the target website
using a two-layer approach:
1. Sitemap Lastmod: Fast check for modified URLs.
2. Content Hashing: Precise check of actual book data (Title, Price, Description)
   to avoid unnecessary database updates.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from app.scraper.monitor_service import MonitorService
from app.scraper.scraper_service import ScraperService
from app.scraper.transformer import VivatTransformer

async def main():
    print("--- Change Detection Demonstration ---")
    
    scraper = ScraperService()
    monitor = MonitorService(scraper)
    transformer = VivatTransformer()
    
    try:
        # 1. Fetch and Parse Sitemap
        print("\nStep 1: Fetching and parsing the sitemap index...")
        # For demonstration, we'll only scan the primary sitemap
        xml_content = await monitor.fetch_sitemap()
        entries = monitor.parse_sitemap(xml_content)
        
        # Filter for book product pages
        book_urls = monitor.filter_product_urls(entries)
        print(f"Discovered {len(book_urls)} product URLs in the sitemap.")

        # 2. Simulate "Known" products
        print("\nStep 2: Simulating known state (as if we have been running for a while)...")
        # Let's pretend we know the first 10 URLs
        simulated_known_urls = {entry.url for entry in book_urls[:10]}
        # We'll pretend we checked 5 minutes ago
        last_check_time = datetime.now() - timedelta(minutes=5)
        
        monitor.load_known_state(simulated_known_urls, {})
        print(f"System 'knows' {len(simulated_known_urls)} URLs.")

        # 3. Detect Changes
        print("\nStep 3: Checking for changes...")
        changes = await monitor.check_for_changes(last_check=last_check_time)
        
        if not changes:
            print("No changes detected (all sitemap timestamps are older than last check).")
        else:
            print(f"Detected {len(changes)} changes from sitemap timestamps!")
            for change in changes[:5]:
                print(f"  - [{change.change_type.upper()}] URL: {change.url}")

        # 4. Deep Content Hashing
        print("\nStep 4: Demonstrating Content Hashing (Precise Detection)")
        test_url = book_urls[0].url if book_urls else "https://vivat.com.ua/product/twisted-ihry/"
        print(f"Scraping and hashing: {test_url}")
        
        scraped, content_hash = await monitor.scrape_and_hash(test_url)
        print(f"Generated Content SHA-256 (prefix): {content_hash}")
        
        # Explain why we use hashing
        print("\n[Technical Note]")
        print("We use this hash (Title + Price + Description) to determine if we should")
        print("perform a new AI Embedding generation and database UPDATE.")
        print("If the hash matches what's in our DB, we skip the computation to save costs.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
