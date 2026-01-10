"""
================================================================
Data Migration: Old Schema → New Schema
Maps CatalogProduct from old denormalized → new normalized structure
================================================================

Assumptions:
- Old tables still exist (for reference)
- New schema tables already created (from 001, 002 migrations)
- This script runs AFTER schema creation, BEFORE dropping old tables
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime
from typing import Optional
import os
import sys

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/onix_db")

async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def migrate_core_products(session: AsyncSession) -> int:
    """
    Migrate from old catalog_products to new catalog_products.
    Maps denormalized → normalized structure.
    """
    logger.info("Starting core product migration...")
    
    # Query old products (raw SQL for flexibility)
    result = await session.execute(text("""
        SELECT 
            id, isbn13, title, subtitle, product_form_code, 
            publishing_status_code, publisher_name, publication_date,
            language_code, metadata, page_count, weight_g,
            is_active, created_at, updated_at
        FROM OLD_catalog_products
        LIMIT 1000000  -- Adjust batch size as needed
    """))
    
    old_products = result.fetchall()
    count = 0
    
    for old_prod in old_products:
        # Insert into new schema
        await session.execute(text("""
            INSERT INTO catalog_products (
                id, isbn13, isbn10, gtin14, proprietary_id,
                title, subtitle,
                collection_title, collection_issn, part_number,
                product_form_code, product_form_detail_code,
                page_count, width_mm, height_mm, thickness_mm, weight_g,
                language_code,
                publisher_name, publisher_id, imprint_name,
                publishing_status_code, publication_date, out_of_print_date,
                audience_code,
                primary_subject_scheme, primary_subject_code,
                udc_code, bbk_code, dk_018_code,
                metadata,
                created_at, updated_at, is_active
            ) VALUES (
                :id, :isbn13, NULL, NULL, NULL,
                :title, :subtitle,
                NULL, NULL, NULL,
                :product_form_code, NULL,
                :page_count, NULL, NULL, NULL, :weight_g,
                :language_code,
                :publisher_name, NULL, NULL,
                :publishing_status_code, :publication_date, NULL,
                NULL,
                NULL, NULL,
                NULL, NULL, NULL,
                :metadata,
                :created_at, :updated_at, :is_active
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": old_prod.id,
            "isbn13": old_prod.isbn13,
            "title": old_prod.title,
            "subtitle": old_prod.subtitle,
            "product_form_code": old_prod.product_form_code,
            "page_count": old_prod.page_count,
            "weight_g": old_prod.weight_g,
            "language_code": old_prod.language_code,
            "publisher_name": old_prod.publisher_name,
            "publishing_status_code": old_prod.publishing_status_code,
            "publication_date": old_prod.publication_date,
            "metadata": old_prod.metadata or {},
            "created_at": old_prod.created_at,
            "updated_at": old_prod.updated_at,
            "is_active": old_prod.is_active,
        })
        
        count += 1
        if count % 10000 == 0:
            await session.commit()
            logger.info(f"Migrated {count} products...")
    
    await session.commit()
    logger.info(f"✅ Migrated {count} core products")
    return count


async def migrate_contributors(session: AsyncSession) -> int:
    """
    Migrate from OLD_contributors → contributors
    Assumes old schema had product_id, name, role_code
    """
    logger.info("Starting contributor migration...")
    
    result = await session.execute(text("""
        SELECT 
            id, product_id, role_code, sequence_number,
            person_name, person_name_inverted, key_names,
            names_before_key, corporate_name, biographical_note
        FROM OLD_contributors
        LIMIT 5000000
    """))
    
    old_contribs = result.fetchall()
    count = 0
    
    for old_contrib in old_contribs:
        # Determine contributor type
        contributor_type = 'P' if old_contrib.person_name else 'C'
        
        await session.execute(text("""
            INSERT INTO contributors (
                id, product_id, role_code, sequence_number,
                contributor_type, person_name, person_name_inverted,
                key_names, names_before_key, corporate_name,
                biographical_note, created_at
            ) VALUES (
                :id, :product_id, :role_code, :sequence_number,
                :contributor_type, :person_name, :person_name_inverted,
                :key_names, :names_before_key, :corporate_name,
                :biographical_note, NOW()
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": old_contrib.id,
            "product_id": old_contrib.product_id,
            "role_code": old_contrib.role_code or 'A01',
            "sequence_number": old_contrib.sequence_number,
            "contributor_type": contributor_type,
            "person_name": old_contrib.person_name,
            "person_name_inverted": old_contrib.person_name_inverted,
            "key_names": old_contrib.key_names,
            "names_before_key": old_contrib.names_before_key,
            "corporate_name": old_contrib.corporate_name,
            "biographical_note": old_contrib.biographical_note,
        })
        
        count += 1
        if count % 50000 == 0:
            await session.commit()
            logger.info(f"Migrated {count} contributors...")
    
    await session.commit()
    logger.info(f"✅ Migrated {count} contributors")
    return count


async def migrate_subjects(session: AsyncSession) -> int:
    """
    Migrate from OLD_subjects → subjects
    """
    logger.info("Starting subject migration...")
    
    result = await session.execute(text("""
        SELECT 
            id, product_id, scheme_code, subject_code,
            subject_heading_text, is_primary, sequence_number
        FROM OLD_subjects
        LIMIT 5000000
    """))
    
    old_subjects = result.fetchall()
    count = 0
    
    for old_subj in old_subjects:
        await session.execute(text("""
            INSERT INTO subjects (
                id, product_id, scheme_code, subject_code,
                subject_heading_text, is_primary, sequence_number
            ) VALUES (
                :id, :product_id, :scheme_code, :subject_code,
                :subject_heading_text, :is_primary, :sequence_number
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": old_subj.id,
            "product_id": old_subj.product_id,
            "scheme_code": old_subj.scheme_code,
            "subject_code": old_subj.subject_code,
            "subject_heading_text": old_subj.subject_heading_text,
            "is_primary": old_subj.is_primary or False,
            "sequence_number": old_subj.sequence_number,
        })
        
        count += 1
        if count % 50000 == 0:
            await session.commit()
            logger.info(f"Migrated {count} subjects...")
    
    await session.commit()
    logger.info(f"✅ Migrated {count} subjects")
    return count


async def migrate_text_content(session: AsyncSession) -> int:
    """
    Migrate from OLD_text_content → text_content
    """
    logger.info("Starting text content migration...")
    
    result = await session.execute(text("""
        SELECT 
            id, product_id, text_type_code, content,
            author, source_title, created_at
        FROM OLD_text_content
        LIMIT 1000000
    """))
    
    old_texts = result.fetchall()
    count = 0
    
    for old_text in old_texts:
        await session.execute(text("""
            INSERT INTO text_content (
                id, product_id, text_type_code, content,
                author, source_title, created_at
            ) VALUES (
                :id, :product_id, :text_type_code, :content,
                :author, :source_title, :created_at
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": old_text.id,
            "product_id": old_text.product_id,
            "text_type_code": old_text.text_type_code,
            "content": old_text.content,
            "author": old_text.author,
            "source_title": old_text.source_title,
            "created_at": old_text.created_at or datetime.now(),
        })
        
        count += 1
        if count % 50000 == 0:
            await session.commit()
            logger.info(f"Migrated {count} text content...")
    
    await session.commit()
    logger.info(f"✅ Migrated {count} text content")
    return count


async def migrate_media(session: AsyncSession) -> int:
    """
    Migrate from OLD_media_files → media_files
    """
    logger.info("Starting media migration...")
    
    result = await session.execute(text("""
        SELECT 
            id, product_id, resource_content_type_code,
            resource_mode_code, file_format_code, file_link_type,
            file_link, width_px, height_px, file_size_bytes,
            sequence_number, created_at
        FROM OLD_media_files
        LIMIT 1000000
    """))
    
    old_media = result.fetchall()
    count = 0
    
    for old_m in old_media:
        await session.execute(text("""
            INSERT INTO media_files (
                id, product_id, resource_content_type_code,
                resource_mode_code, file_format_code, file_link_type,
                file_link, width_px, height_px, file_size_bytes,
                sequence_number, created_at
            ) VALUES (
                :id, :product_id, :resource_content_type_code,
                :resource_mode_code, :file_format_code, :file_link_type,
                :file_link, :width_px, :height_px, :file_size_bytes,
                :sequence_number, :created_at
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": old_m.id,
            "product_id": old_m.product_id,
            "resource_content_type_code": old_m.resource_content_type_code,
            "resource_mode_code": old_m.resource_mode_code,
            "file_format_code": old_m.file_format_code,
            "file_link_type": old_m.file_link_type,
            "file_link": old_m.file_link,
            "width_px": old_m.width_px,
            "height_px": old_m.height_px,
            "file_size_bytes": old_m.file_size_bytes,
            "sequence_number": old_m.sequence_number,
            "created_at": old_m.created_at or datetime.now(),
        })
        
        count += 1
        if count % 50000 == 0:
            await session.commit()
            logger.info(f"Migrated {count} media files...")
    
    await session.commit()
    logger.info(f"✅ Migrated {count} media files")
    return count


async def run_migration():
    """
    Execute full data migration
    """
    async with AsyncSessionLocal() as session:
        logger.info("=" * 60)
        logger.info("Starting Data Migration: Old → New Schema")
        logger.info("=" * 60)
        
        try:
            # Migrate in order (dependencies first)
            products_count = await migrate_core_products(session)
            contributors_count = await migrate_contributors(session)
            subjects_count = await migrate_subjects(session)
            text_count = await migrate_text_content(session)
            media_count = await migrate_media(session)
            
            logger.info("=" * 60)
            logger.info("✅ Migration Complete!")
            logger.info(f"   Products: {products_count}")
            logger.info(f"   Contributors: {contributors_count}")
            logger.info(f"   Subjects: {subjects_count}")
            logger.info(f"   Text Content: {text_count}")
            logger.info(f"   Media Files: {media_count}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_migration())
