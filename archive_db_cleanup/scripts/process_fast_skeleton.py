"""
Fast Skeleton Loader.
Uses `transformer_skeleton` to quickly populate the DB with Products and Prices.
Does NOT load heavy metadata (Descriptions, Authors, Series).
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parents[1]))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.scraper.yakaboo.transformer_skeleton import transform_skeleton
from app.services.market_loader import MarketLoader
from app.models.catalog import CatalogProduct, CatalogTitle
from app.models.codes import ProductForm, TitleType

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - SKELETON - %(message)s"
)
logger = logging.getLogger(__name__)

INPUT_FILE = "data/yakaboo_complete_final.jsonl"
LIMIT = 1 # ONLY ONE RECORD FOR DEBUGGING

async def process_skeleton():
    logger.info(f"Starting FAST SKELETON load (Limit: {LIMIT})...")
    
    async with AsyncSessionLocal() as session:
        market_loader = MarketLoader(session)
        count = 0
        new_products = 0
        
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if count >= LIMIT:
                    break
                try:
                    raw = json.loads(line)
                    skel = transform_skeleton(raw)
                    
                    # 1. Fast Upsert CatalogProduct (Skeleton only)
                    product_id = None
                    
                    stmt = select(CatalogProduct.id).where(
                        (CatalogProduct.isbn_13 == skel.isbn) | 
                        (CatalogProduct.record_reference == f"yakaboo_{skel.source_id}")
                    )
                    res = await session.execute(stmt)
                    existing_id = res.scalar_one_or_none()
                    
                    if existing_id:
                        product_id = existing_id
                        logger.info(f"Found existing product: {product_id}")
                    else:
                        new_products += 1
                        product_id = uuid4()
                        
                        # ORM Approach (Safer than pg_insert for types)
                        new_product = CatalogProduct(
                            id=product_id,
                            record_reference=f"yakaboo_{skel.source_id}",
                            isbn_13=skel.isbn,
                            ean=skel.ean,
                            sku=skel.sku,
                            product_form=ProductForm.BOOK,
                            is_ukrainian=True
                        )
                        session.add(new_product)
                        
                        # Add Title
                        if skel.title:
                            new_title = CatalogTitle(
                                product_id=product_id,
                                type=TitleType.DISTINCTIVE_TITLE_BOOK_COVER_TITLE_SERIAL_TITLE_OF_CONTENT_ITEM_COLLECTION_OR_RESOURCE,
                                title_text=skel.title
                            )
                            session.add(new_title)

                        await session.flush() # Force DB write to check constraints immediately
                    
                    # 2. Update Market Data
                    await market_loader.update_price(
                        book_id=product_id,
                        supplier_code="yakaboo",
                        sku=skel.source_id,
                        price=skel.price,
                        price_old=skel.old_price,
                        url=skel.url,
                        in_stock=skel.in_stock
                    )
                    
                    count += 1
                    # Commit per record for debug
                    await session.commit()
                    logger.info(f"✅ Processed record {count}: {skel.title}")
                        
                except Exception as e:
                    logger.error(f"❌ Error on record {count}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Important: Rollback on error so we can continue or exit clean
                    await session.rollback()

if __name__ == "__main__":
    asyncio.run(process_skeleton())