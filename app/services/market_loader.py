"""
Market Loader Service.
Handles high-frequency updates of Prices and Stock (Offers).
"""

from decimal import Decimal
from typing import Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.market import Offer, PriceHistory, Supplier, ProductAvailability

class MarketLoader:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._supplier_cache = {}

    async def get_supplier_id(self, code: str, name: str, base_url: str = None) -> UUID:
        """Get or create supplier by code."""
        if code in self._supplier_cache:
            return self._supplier_cache[code]

        stmt = select(Supplier).where(Supplier.code == code)
        result = await self.session.execute(stmt)
        supplier = result.scalar_one_or_none()

        if not supplier:
            supplier = Supplier(name=name, code=code, base_url=base_url)
            self.session.add(supplier)
            await self.session.flush() # Get ID
        
        self._supplier_cache[code] = supplier.id
        return supplier.id

    async def update_price(
        self,
        book_id: UUID,
        supplier_code: str,
        sku: str,
        price: float,
        url: str,
        in_stock: bool,
        currency: str = "UAH",
        price_old: Optional[float] = None
    ):
        """
        Upsert Offer and log to PriceHistory.
        """
        supplier_id = await self.get_supplier_id(supplier_code, supplier_code.capitalize()) # Simple name fallback

        # 1. Upsert Offer
        # We use PostgreSQL specific ON CONFLICT to handle high concurrency updates
        stmt = pg_insert(Offer).values(
            book_id=book_id,
            supplier_id=supplier_id,
            sku=sku,
            url=url,
            price=price,
            price_old=price_old,
            currency=currency,
            in_stock=in_stock,
            availability=ProductAvailability.IN_STOCK if in_stock else ProductAvailability.OUT_OF_STOCK,
            last_updated=datetime.now()
        ).on_conflict_do_update(
            index_elements=['book_id', 'supplier_id'],
            set_={
                "price": price,
                "price_old": price_old,
                "in_stock": in_stock,
                "last_updated": datetime.now(),
                "url": url # Update URL just in case
            }
        ).returning(Offer.id)

        result = await self.session.execute(stmt)
        offer_id = result.scalar_one()

        # 2. Append to History (Always, or optimized to only if changed? 
        # For V3 we append always or check diff. Let's append for analytics)
        # To save space, usually we check if price changed. But for now, simple log.
        
        history = PriceHistory(
            offer_id=offer_id,
            price=price,
            currency=currency,
            availability=ProductAvailability.IN_STOCK if in_stock else ProductAvailability.OUT_OF_STOCK,
            recorded_at=datetime.now()
        )
        self.session.add(history)
