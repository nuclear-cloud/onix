
import asyncio
import json
import sys
import os

sys.path.append(os.getcwd())

from app.scraper.scraper_service import ScraperService

async def inspect_images():
    url = "https://vivat.com.ua/product/twisted-ihry/"
    print(f"Scraping {url}...")
    
    scraper = ScraperService()
    try:
        data = await scraper.scrape_product(url)
        pj = data.raw_json
        
        print("\n--- IMAGE KEYS ---")
        if "image" in pj:
            print(f"Main 'image': {pj['image']}")
            
        if "slideShow" in pj:
            print(f"Found 'slideShow' with {len(pj['slideShow'])} items:")
            print(json.dumps(pj['slideShow'], indent=2, ensure_ascii=False))
            
        if "gallery" in pj:
             print(f"Found 'gallery': {pj['gallery']}")
             
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(inspect_images())
