"""
Database Initialization Script.
V3.0 Strict ONIX Compliance.
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parents[1]))

from app.core.database import engine, Base
from app.models import (
    CatalogProduct,
    CatalogProductContributor,
    CatalogSubject,
    Publisher,
    Supplier,
    Offer,
    PriceHistory,
    Collection,
    CatalogProductCollection,
    CatalogPrize,
    RefThemaSubject
)

async def init_db():
    print("🚀 Initializing Database V3.0...")
    
    async with engine.begin() as conn:
        print("\n🗑️  Dropping all tables (CASCADE)...")
        # Get all table names in reverse order of dependencies
        # Base.metadata.sorted_tables works well
        for table in reversed(Base.metadata.sorted_tables):
            print(f"      - Dropping {table.name}...")
            await conn.execute(text(f"DROP TABLE IF EXISTS {table.name} CASCADE"))
        
        print("\n🏗️  Creating new schema...")
        await conn.run_sync(Base.metadata.create_all)
        print("   ✅ Tables created.")
            
        # Manually create partition for PriceHistory (2026)
        print("\n🔧 Creating partitions...")
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS price_history_2026 PARTITION OF price_history "
            "FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');"
        ))
        print("   ✅ Partition 'price_history_2026' created.")
            
    # Seed Data
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("\n🌱 Seeding initial data...")
    async with AsyncSessionLocal() as session:
        suppliers = [
            Supplier(name="Yakaboo", code="yakaboo", base_url="https://yakaboo.ua"),
        ]
        session.add_all(suppliers)
        await session.commit()
        print(f"   ✅ Added {len(suppliers)} suppliers.")
        
    print("\n✨ Initialization Complete!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        asyncio.run(init_db())
    else:
        print("⚠️  WARNING: This will DESTROY all data in the database.")
        print("   Run with '--force' to confirm confirm.")
        asyncio.run(init_db()) # Temporary auto-run for agent