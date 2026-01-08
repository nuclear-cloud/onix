"""
Market Models (Dynamic Data) - V2.1 High Performance.

Changes:
- Added `currency` to PriceHistory.
- Enabled PostgreSQL Partitioning for PriceHistory (Range by recorded_at).
- UUIDv7 readiness notes.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, func, Boolean, DECIMAL, Enum as SQLEnum, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.codes_v71 import ProductAvailability, PriceType

class Supplier(Base):
    """
    Store registry (e.g. Yakaboo, Knygarnya Ye, Vivat).
    """
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True) # e.g. 'yakaboo'
    base_url = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    offers = relationship("Offer", back_populates="supplier")


class Offer(Base):
    """
    Current Market State (Hot Table).
    Represents 1 product at 1 supplier.
    Optimized for high-frequency updates (UPSERT).
    """
    __tablename__ = "offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Links
    book_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id"), nullable=False, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    
    # External ID in store (for parsing/matching)
    sku = Column(String(100), nullable=True) # e.g. Yakaboo ID
    url = Column(Text, nullable=True)
    
    # Price & Stock
    price = Column(DECIMAL(10, 2), nullable=False)
    price_old = Column(DECIMAL(10, 2), nullable=True)
    currency = Column(String(3), default="UAH")
    
    availability = Column(SQLEnum(ProductAvailability), default=ProductAvailability.AVAILABLE)
    in_stock = Column(Boolean, default=True)
    
    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    
    # Relationships
    product = relationship("app.models.catalog.CatalogProduct") 
    supplier = relationship("Supplier", back_populates="offers")
    history = relationship("PriceHistory", back_populates="offer", cascade="all, delete-orphan")

    # Constraints: One offer per book per supplier
    __table_args__ = (
        UniqueConstraint('book_id', 'supplier_id', name='uq_offer_book_supplier'),
    )


class PriceHistory(Base):
    """
    Historical Price Log (Cold Table).
    Append-only. Used for analytics and charts.
    
    PARTITIONING:
    This table is partitioned by RANGE (recorded_at).
    SQLAlchemy requires manual DDL setup for partitions usually, 
    but we declare the intent here.
    """
    __tablename__ = "price_history"
    __table_args__ = (
        {
            "postgresql_partition_by": "RANGE (recorded_at)"
        }
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Note: Foreign Keys in partitioned tables can be tricky in older PG versions,
    # but valid in PG12+ if the reference is included in the partition key (which it isn't here).
    # Ideally, we drop FK constraint for pure log performance or handle it carefully.
    # keeping FK for data integrity now, assuming PG14+.
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    price = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="UAH") # Added currency support
    availability = Column(SQLEnum(ProductAvailability), nullable=True)
    
    recorded_at = Column(DateTime(timezone=True), primary_key=True, server_default=func.now(), index=True, nullable=False)
    
    offer = relationship("Offer", back_populates="history")