
import asyncio
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal, engine, Base
from app.scraper.scraper_service import ScraperService
from app.scraper.transformer import VivatTransformer
from app.services.product_service import ProductService

async def main():
    # 1. Ensure tables exist (for development/demo)
    print("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    url = "https://vivat.com.ua/product/twisted-ihry/"
    print(f"\nScraping URL: {url}...")
    
    scraper = ScraperService()
    transformer = VivatTransformer()
    
    try:
        # 2. Scrape
        scraped_data = await scraper.scrape_product(url)
        print("Scrape successful!")
        
        # 3. Transform
        product_create = transformer.transform(scraped_data)
        author_names = transformer.extract_authors(scraped_data.raw_json)
        
        print(f"Detected Authors: {author_names}")
        
        # 4. Save to DB
        async with AsyncSessionLocal() as db:
            service = ProductService(db)
            print("Ingesting into database...")
            
            db_product = await service.ingest_product(product_create, author_names)
            
            if db_product:
                print(f"\n✅ SUCCESS!")
                print(f"Product saved with ID: {db_product.id}")
                print(f"Title: {db_product.title}")
                print(f"ISBN: {db_product.isbn_13}")
                print(f"Content Hash: {db_product.onix_json.get('extra', {}).get('content_hash')}")
            else:
                print("\n⚠️ Product already exists or validation failed.")
                
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
