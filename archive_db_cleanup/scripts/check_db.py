import asyncio
import logging
import sys
from pathlib import Path
from sqlalchemy import select, func

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.catalog import CatalogProduct
from app.models.market import Offer, PriceHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_db_stats():
    async with AsyncSessionLocal() as session:
        # Count Products
        result_products = await session.execute(select(func.count(CatalogProduct.id)))
        count_products = result_products.scalar()
        
        # Count Offers
        result_offers = await session.execute(select(func.count(Offer.id)))
        count_offers = result_offers.scalar()

        # Count Price History
        result_history = await session.execute(select(func.count(PriceHistory.recorded_at)))
        count_history = result_history.scalar()
        
        print("-" * 40)
        print(f"📊 DATABASE STATISTICS (V2)")
        print("-" * 40)
        print(f"📚 Catalog Products: {count_products:,}")
        print(f"🏷️  Market Offers:    {count_offers:,}")
        print(f"📈 Price History:    {count_history:,}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(check_db_stats())

