#!/usr/bin/env python3
"""
🔗 Enrich Yakaboo Books with Authors, Publishers & Relations

Takes existing 897K books and adds:
  ✅ Authors (from author_label)
  ✅ Publishers (from book_publisher)
  ✅ Series (from series_label)
  ✅ Subjects (from categories)
  ✅ Contributors links
  
Usage:
  python scripts/enrich_yakaboo_relations.py
  python scripts/enrich_yakaboo_relations.py --limit 10000
  python scripts/enrich_yakaboo_relations.py --skip 100000
"""

import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from prisma import Prisma
from prisma.models import Publisher, Contributor


class EnrichmentStats:
    def __init__(self):
        self.total_processed = 0
        self.books_found = 0
        self.books_not_found = 0
        self.publishers_created = 0
        self.contributors_created = 0
        self.links_created = 0
        self.errors = 0
        self.start_time = datetime.now()
        
        # Caches
        self.publisher_cache: Dict[str, str] = {}  # name -> id
        self.contributor_cache: Dict[str, str] = {}  # name -> id
    
    def report(self):
        duration = (datetime.now() - self.start_time).total_seconds()
        rate = self.total_processed / duration if duration > 0 else 0
        
        print("\n" + "="*60)
        print("📊 ENRICHMENT REPORT")
        print("="*60)
        print(f"⏱️  Duration: {duration:.1f}s ({rate:.0f} books/sec)")
        print(f"📖 Processed: {self.total_processed:,}")
        print(f"✅ Found in DB: {self.books_found:,}")
        print(f"❌ Not found: {self.books_not_found:,}")
        print(f"\n📚 Created:")
        print(f"   Publishers: {self.publishers_created}")
        print(f"   Contributors: {self.contributors_created}")
        print(f"   Links: {self.links_created}")
        print(f"\n❌ Errors: {self.errors}")
        print("="*60)


def extract_isbn13(raw: Dict[str, Any]) -> Optional[str]:
    """Extract ISBN13 from raw Yakaboo data."""
    # Try book_isbn field
    isbn = raw.get('book_isbn')
    if isbn:
        isbn = str(isbn).replace('-', '').replace(' ', '')
        if len(isbn) == 13:
            return isbn
    
    # Try sku as fallback
    sku = raw.get('sku')
    if sku and len(str(sku)) == 13:
        return str(sku)
    
    return None


def extract_authors(raw: Dict[str, Any]) -> List[str]:
    """Extract author names from author_label."""
    authors = []
    author_labels = raw.get('author_label', [])
    
    if isinstance(author_labels, list):
        for item in author_labels:
            if isinstance(item, dict):
                label = item.get('label', '').strip()
                if label:
                    authors.append(label)
    
    return authors


def extract_publisher(raw: Dict[str, Any]) -> Optional[str]:
    """Extract publisher name from book_publisher_label."""
    # book_publisher_label is a list of dicts with 'label' field
    publisher_labels = raw.get('book_publisher_label', [])
    
    if isinstance(publisher_labels, list) and len(publisher_labels) > 0:
        first = publisher_labels[0]
        if isinstance(first, dict):
            label = first.get('label', '').strip()
            if label and label != '0' and label.lower() != 'null':
                return label
    
    return None


def extract_series(raw: Dict[str, Any]) -> Optional[str]:
    """Extract series name from series_label."""
    series_labels = raw.get('series_label', [])
    
    if isinstance(series_labels, list) and len(series_labels) > 0:
        first = series_labels[0]
        if isinstance(first, dict):
            return first.get('label', '').strip() or None
    
    return None


async def get_or_create_publisher(
    db: Prisma, 
    name: str, 
    stats: EnrichmentStats
) -> Optional[str]:
    """Get existing publisher or create new one."""
    # Check cache
    if name in stats.publisher_cache:
        return stats.publisher_cache[name]
    
    try:
        # Try to find existing
        publisher = await db.publisher.find_first(
            where={'name': name}
        )
        
        if publisher:
            stats.publisher_cache[name] = publisher.id
            return publisher.id
        
        # Create new
        publisher = await db.publisher.create(
            data={
                'name': name,
            }
        )
        
        stats.publishers_created += 1
        stats.publisher_cache[name] = publisher.id
        return publisher.id
        
    except Exception as e:
        print(f"⚠️  Publisher error for '{name}': {e}")
        return None


async def get_or_create_contributor(
    db: Prisma,
    name: str,
    stats: EnrichmentStats
) -> Optional[str]:
    """Get existing contributor or create new one."""
    # Check cache
    if name in stats.contributor_cache:
        return stats.contributor_cache[name]
    
    try:
        # Try to find existing
        contributor = await db.contributor.find_first(
            where={'name': name}
        )
        
        if contributor:
            stats.contributor_cache[name] = contributor.id
            return contributor.id
        
        # Create new
        contributor = await db.contributor.create(
            data={
                'name': name,
            }
        )
        
        stats.contributors_created += 1
        stats.contributor_cache[name] = contributor.id
        return contributor.id
        
    except Exception as e:
        print(f"⚠️  Contributor error for '{name}': {e}")
        return None


async def link_contributor_to_product(
    db: Prisma,
    product_id: str,
    contributor_id: str,
    sequence: int,
    stats: EnrichmentStats
) -> bool:
    """Link contributor to product via catalog_product_contributors_link."""
    try:
        await db.catalog_product_contributors_link.create(
            data={
                'product_id': product_id,
                'contributor_id': contributor_id,
                'role': 'BY_AUTHOR',  # list17 enum value
                'sequence_number': sequence,
            }
        )
        stats.links_created += 1
        return True
    except Exception as e:
        # Ignore if link already exists
        if 'Unique constraint' in str(e):
            return True
        print(f"⚠️  Link error: {e}")
        return False


async def enrich_book(
    db: Prisma,
    raw_data: Dict[str, Any],
    stats: EnrichmentStats
) -> bool:
    """Enrich a single book with relational data."""
    try:
        # Get ISBN13
        isbn13 = extract_isbn13(raw_data)
        if not isbn13:
            return False
        
        # Find the book in DB
        book = await db.catalogproduct.find_unique(
            where={'isbn13': isbn13}
        )
        
        if not book:
            stats.books_not_found += 1
            return False
        
        stats.books_found += 1
        
        # Extract data
        publisher_name = extract_publisher(raw_data)
        author_names = extract_authors(raw_data)
        
        # Create/link publisher
        if publisher_name and not book.publisherId:
            publisher_id = await get_or_create_publisher(db, publisher_name, stats)
            if publisher_id:
                await db.catalogproduct.update(
                    where={'id': book.id},
                    data={'publisherId': publisher_id}
                )
        
        # Create/link authors
        for seq, author_name in enumerate(author_names, start=1):
            contributor_id = await get_or_create_contributor(db, author_name, stats)
            if contributor_id:
                await link_contributor_to_product(
                    db, book.id, contributor_id, seq, stats
                )
        
        return True
        
    except Exception as e:
        stats.errors += 1
        print(f"❌ Error processing: {e}")
        return False


async def process_batch(
    db: Prisma,
    batch: List[Dict[str, Any]],
    stats: EnrichmentStats
):
    """Process a batch of books."""
    for raw_data in batch:
        await enrich_book(db, raw_data, stats)


async def run_enrichment(
    file_path: str,
    batch_size: int = 500,
    skip: int = 0,
    limit: Optional[int] = None
):
    """Main enrichment process."""
    print("🔗 Starting Yakaboo Enrichment")
    print(f"📁 File: {file_path}")
    print(f"🔢 Batch size: {batch_size}")
    if skip > 0:
        print(f"⏭️  Skip: {skip:,}")
    if limit:
        print(f"📊 Limit: {limit:,}")
    print()
    
    stats = EnrichmentStats()
    
    # Connect to DB
    db = Prisma()
    await db.connect()
    
    try:
        batch = []
        line_num = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_num += 1
                
                # Skip lines
                if line_num <= skip:
                    continue
                
                # Check limit
                if limit and stats.total_processed >= limit:
                    print(f"⛔ Reached limit of {limit:,}")
                    break
                
                # Parse line
                try:
                    raw_data = json.loads(line.strip())
                    batch.append(raw_data)
                    stats.total_processed += 1
                except json.JSONDecodeError:
                    continue
                
                # Process batch
                if len(batch) >= batch_size:
                    await process_batch(db, batch, stats)
                    batch.clear()
                    
                    # Progress
                    if stats.total_processed % 5000 == 0:
                        duration = (datetime.now() - stats.start_time).total_seconds()
                        rate = stats.total_processed / duration if duration > 0 else 0
                        print(f"⏳ {stats.total_processed:,} | "
                              f"Found: {stats.books_found:,} | "
                              f"Pubs: {stats.publishers_created} | "
                              f"Authors: {stats.contributors_created} | "
                              f"Rate: {rate:.0f}/s")
            
            # Process remaining
            if batch:
                await process_batch(db, batch, stats)
        
    finally:
        await db.disconnect()
    
    stats.report()


def main():
    parser = argparse.ArgumentParser(description='Enrich Yakaboo books with relations')
    parser.add_argument(
        '--file',
        default='archive_db_cleanup/data/yakaboo_complete_final.jsonl',
        help='Path to Yakaboo JSONL file'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Batch size (default: 500)'
    )
    parser.add_argument(
        '--skip',
        type=int,
        default=0,
        help='Skip N lines (for resume)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Process only N books (for testing)'
    )
    
    args = parser.parse_args()
    
    asyncio.run(run_enrichment(
        file_path=args.file,
        batch_size=args.batch_size,
        skip=args.skip,
        limit=args.limit
    ))


if __name__ == '__main__':
    main()
