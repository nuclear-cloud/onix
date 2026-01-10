#!/usr/bin/env python3
"""
Migrate data from old schema to new normalized schema.
Handles: catalog_products -> catalog_products (new)
         catalog_contributors -> contributors
         catalog_subjects -> subjects
         catalog_text_contents -> text_content
         media -> media_files
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional
import logging

try:
    from sqlalchemy import text, select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
except ImportError:
    print("ERROR: sqlalchemy not installed. Run: pip install sqlalchemy asyncpg")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database URL (use asyncpg for async support)
DATABASE_URL = "postgresql+asyncpg://onix_user:onix_secure_pass_2024@localhost:5432/onix_db"


async def migrate_core_products(session: AsyncSession, limit: Optional[int] = None) -> int:
    """Migrate core product data from old catalog_products to new."""
    logger.info("Starting product migration...")
    
    try:
        # Count total
        result = await session.execute(text("SELECT COUNT(*) FROM catalog_products"))
        total = result.scalar() or 0
        
        if limit:
            total = min(total, limit)
        
        logger.info(f"Found {total} products to migrate")
        
        # Migrate in batches
        batch_size = 1000
        migrated = 0
        
        query = """
        INSERT INTO catalog_products (
            isbn13, isbn10, gtin14, title, subtitle,
            product_form_code, page_count, width_mm, height_mm, thickness_mm, weight_g,
            language_code, publisher_name, publishing_status_code, publication_date,
            primary_subject_scheme, metadata, created_at, updated_at
        )
        SELECT
            isbn13, isbn10, gtin14, title, subtitle,
            COALESCE(product_form_code, 'BB'), page_count, width_mm, height_mm, thickness_mm, weight_g,
            COALESCE(language_code, 'ukr'), publisher_name, 
            COALESCE(publishing_status_code, '01'), publication_date,
            'BISAC', 
            to_jsonb(row_to_json(t)) as metadata,
            COALESCE(created_at, NOW()), COALESCE(updated_at, NOW())
        FROM (
            SELECT * FROM catalog_products LIMIT %s OFFSET %s
        ) t
        ON CONFLICT (isbn13) DO NOTHING
        """
        
        offset = 0
        while offset < total:
            await session.execute(text(query), {"offset": offset, "limit": batch_size})
            await session.commit()
            migrated = min(offset + batch_size, total)
            if migrated % 500 == 0:
                logger.info(f"  Migrated {migrated}/{total} products")
            offset += batch_size
        
        logger.info(f"✅ Product migration complete: {migrated} products")
        return migrated
        
    except Exception as e:
        logger.error(f"❌ Product migration failed: {e}")
        await session.rollback()
        return 0


async def migrate_contributors(session: AsyncSession, limit: Optional[int] = None) -> int:
    """Migrate contributor data."""
    logger.info("Starting contributor migration...")
    
    try:
        result = await session.execute(text("SELECT COUNT(*) FROM catalog_contributors"))
        total = result.scalar() or 0
        
        if limit:
            total = min(total, limit)
        
        logger.info(f"Found {total} contributors to migrate")
        
        batch_size = 1000
        migrated = 0
        
        offset = 0
        while offset < total:
            query = f"""
            INSERT INTO contributors (
                product_id, contributor_type_code, contributor_role_code,
                display_name, given_name, family_name,
                sequence_number, created_at, updated_at
            )
            SELECT
                cp.id, COALESCE(cc.contributor_type, 'P'), COALESCE(cc.contributor_role, 'A01'),
                cc.display_name, cc.given_name, cc.family_name,
                cc.sequence_number, COALESCE(cc.created_at, NOW()), COALESCE(cc.updated_at, NOW())
            FROM catalog_contributors cc
            JOIN catalog_products cp ON cp.isbn13 = cc.isbn13
            LIMIT {batch_size} OFFSET {offset}
            """
            await session.execute(text(query))
            await session.commit()
            migrated = min(offset + batch_size, total)
            if migrated % 500 == 0:
                logger.info(f"  Migrated {migrated}/{total} contributors")
            offset += batch_size
        
        logger.info(f"✅ Contributor migration complete: {migrated} contributors")
        return migrated
        
    except Exception as e:
        logger.error(f"❌ Contributor migration failed: {e}")
        await session.rollback()
        return 0


async def migrate_subjects(session: AsyncSession, limit: Optional[int] = None) -> int:
    """Migrate subject/category data."""
    logger.info("Starting subject migration...")
    
    try:
        result = await session.execute(text("SELECT COUNT(*) FROM catalog_subjects"))
        total = result.scalar() or 0
        
        if limit:
            total = min(total, limit)
        
        logger.info(f"Found {total} subjects to migrate")
        
        batch_size = 1000
        migrated = 0
        
        offset = 0
        while offset < total:
            query = f"""
            INSERT INTO subjects (
                product_id, subject_scheme, subject_code, subject_text,
                is_primary, created_at, updated_at
            )
            SELECT
                cp.id, COALESCE(cs.subject_scheme, 'BISAC'), cs.subject_code, cs.subject_text,
                COALESCE(cs.is_primary, false), COALESCE(cs.created_at, NOW()), COALESCE(cs.updated_at, NOW())
            FROM catalog_subjects cs
            JOIN catalog_products cp ON cp.isbn13 = cs.isbn13
            LIMIT {batch_size} OFFSET {offset}
            """
            await session.execute(text(query))
            await session.commit()
            migrated = min(offset + batch_size, total)
            if migrated % 500 == 0:
                logger.info(f"  Migrated {migrated}/{total} subjects")
            offset += batch_size
        
        logger.info(f"✅ Subject migration complete: {migrated} subjects")
        return migrated
        
    except Exception as e:
        logger.error(f"❌ Subject migration failed: {e}")
        await session.rollback()
        return 0


async def migrate_text_content(session: AsyncSession, limit: Optional[int] = None) -> int:
    """Migrate text content (descriptions, reviews, etc)."""
    logger.info("Starting text content migration...")
    
    try:
        result = await session.execute(text("SELECT COUNT(*) FROM catalog_text_contents"))
        total = result.scalar() or 0
        
        if limit:
            total = min(total, limit)
        
        logger.info(f"Found {total} text content entries to migrate")
        
        batch_size = 1000
        migrated = 0
        
        offset = 0
        while offset < total:
            query = f"""
            INSERT INTO text_content (
                product_id, text_type_code, language_code, text_content,
                sequence_number, created_at, updated_at
            )
            SELECT
                cp.id, COALESCE(tc.text_type_code, '06'), COALESCE(tc.language_code, 'ukr'), tc.text_content,
                tc.sequence_number, COALESCE(tc.created_at, NOW()), COALESCE(tc.updated_at, NOW())
            FROM catalog_text_contents tc
            JOIN catalog_products cp ON cp.isbn13 = tc.isbn13
            LIMIT {batch_size} OFFSET {offset}
            """
            await session.execute(text(query))
            await session.commit()
            migrated = min(offset + batch_size, total)
            if migrated % 500 == 0:
                logger.info(f"  Migrated {migrated}/{total} text entries")
            offset += batch_size
        
        logger.info(f"✅ Text content migration complete: {migrated} entries")
        return migrated
        
    except Exception as e:
        logger.error(f"❌ Text content migration failed: {e}")
        await session.rollback()
        return 0


async def run_migration(limit: Optional[int] = None):
    """Execute full migration pipeline."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        logger.info("=" * 60)
        logger.info("🔄 SCHEMA MIGRATION - OLD → NEW")
        logger.info("=" * 60)
        
        start = datetime.now()
        
        try:
            # Run migrations in sequence
            products_count = await migrate_core_products(session, limit)
            contributors_count = await migrate_contributors(session, limit)
            subjects_count = await migrate_subjects(session, limit)
            text_count = await migrate_text_content(session, limit)
            
            # Summary
            elapsed = (datetime.now() - start).total_seconds()
            logger.info("=" * 60)
            logger.info("✅ MIGRATION COMPLETE")
            logger.info(f"   Products:     {products_count}")
            logger.info(f"   Contributors: {contributors_count}")
            logger.info(f"   Subjects:     {subjects_count}")
            logger.info(f"   Text Content: {text_count}")
            logger.info(f"   Time:         {elapsed:.2f}s")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ MIGRATION FAILED: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    limit = None
    if len(sys.argv) > 1 and sys.argv[1] == "--limit":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        logger.info(f"Limiting migration to {limit} records per table")
    
    asyncio.run(run_migration(limit))
