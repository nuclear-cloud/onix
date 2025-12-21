
import asyncio
import sys
import json
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.scraper.scraper_service import ScraperService
from app.scraper.transformer import VivatTransformer

async def main():
    # A real Vivat product URL (example: George Orwell - 1984)
    # If this specific URL doesn't work, we might need to find another one from the sitemap.
    url = "https://vivat.com.ua/product/twisted-ihry/"
    
    print(f"Scraping URL: {url}...")
    
    scraper = ScraperService()
    try:
        scraped_data = await scraper.scrape_product(url)
        print("Scrape successful!")
        print("\n--- RAW DATA FROM VIVAT (RAW JSON) ---")
        print(json.dumps(scraped_data.raw_json, indent=2, ensure_ascii=False))
        
        print(f"\nTitle from Raw JSON: {scraped_data.raw_json.get('title')}")
        
        print("\nTransforming to ONIX...")
        transformer = VivatTransformer()
        product = transformer.transform(scraped_data)
        
        print("\n--- PASSED DATA ---")
        print(f"Title: {product.title}")
        print(f"ISBN: {product.isbn_13}")
        print(f"Format: {product.product_form}")
        
        print("\n--- ONIX DETAILS ---")
        if product.onix_json:
            if product.onix_json.subjects:
                print(f"Subjects: {[s.subject_heading_text for s in product.onix_json.subjects]}")
            else:
                print("Subjects: None")
                
            if product.onix_json.extents:
                print(f"Extents: {product.onix_json.extents}")
            else:
                print("Extents: None")
                
            if product.onix_json.measures:
                print(f"Measures: {product.onix_json.measures}")
            else:
                print("Measures: None")
                
            if product.onix_json.supply_details:
                print(f"Availability: {product.onix_json.supply_details[0].product_availability}")
            else:
                print("Availability: None")

            if product.onix_json.supporting_resources:
                print("\n--- IMAGES & SAMPLES ---")
                for res in product.onix_json.supporting_resources:
                    type_map = {"01": "Cover", "07": "Image", "15": "Sample"}
                    print(f"Type: {type_map.get(res.resource_content_type, res.resource_content_type)} | URL: {res.resource_link}")

        print("\n--- FULL DATA DUMP ---")
        # Dump the Pydantic model to JSON
        print(product.model_dump_json(indent=2, exclude_none=True))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(main())
