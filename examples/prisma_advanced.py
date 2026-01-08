#!/usr/bin/env python3
"""
Advanced Prisma Examples - Complex Queries and Relations

This demonstrates advanced Prisma usage including:
- Filtering and pagination
- Sorting
- Relations (joins)
- Aggregations
- Batch operations
"""

import asyncio
from datetime import datetime
from prisma import Prisma
from prisma.models import CatalogProduct


async def filtering_and_pagination(db: Prisma):
    """Demonstrate complex filtering and pagination."""
    print("\n" + "="*70)
    print("1. FILTERING AND PAGINATION")
    print("="*70)
    
    # Pagination with filters
    hardbacks = await db.catalogproduct.find_many(
        where={
            'productForm': 'HARDBACK',
            'isbn13': {'not': None}
        },
        take=10,
        skip=0,
        order={'createdAt': 'desc'}
    )
    
    print(f"\n📘 First 10 hardback books:")
    for book in hardbacks:
        print(f"   • {book.isbn13} - Form: {book.productForm}")
    
    # Count with filters
    hardback_count = await db.catalogproduct.count(
        where={'productForm': 'HARDBACK'}
    )
    print(f"\n📊 Total hardbacks: {hardback_count:,}")


async def relations_example(db: Prisma):
    """Query with relations (publisher, titles, etc)."""
    print("\n" + "="*70)
    print("2. RELATIONS (JOIN QUERIES)")
    print("="*70)
    
    # Get book with related data
    books_with_publisher = await db.catalogproduct.find_many(
        where={
            'publisherId': {'not': None},
            'isbn13': {'not': None}
        },
        include={
            'publisher': True,  # Join with publisher table
            'titles': True      # Join with titles table
        },
        take=5
    )
    
    print(f"\n📚 Books with publisher info:")
    for book in books_with_publisher:
        publisher_name = book.publisher.name if book.publisher else "N/A"
        titles = [t.titleText for t in book.titles] if book.titles else []
        title = titles[0] if titles else "No title"
        
        print(f"\n   📖 {book.isbn13}")
        print(f"      Title: {title[:60]}...")
        print(f"      Publisher: {publisher_name}")


async def aggregations(db: Prisma):
    """Demonstrate aggregation queries."""
    print("\n" + "="*70)
    print("3. AGGREGATIONS")
    print("="*70)
    
    # Count books with/without publisher
    with_publisher = await db.catalogproduct.count(
        where={'publisherId': {'not': None}}
    )
    without_publisher = await db.catalogproduct.count(
        where={'publisherId': None}
    )
    
    print(f"\n📊 Publisher statistics:")
    print(f"   With publisher: {with_publisher:,}")
    print(f"   Without publisher: {without_publisher:,}")
    
    # Count by Ukrainian flag
    ukrainian = await db.catalogproduct.count(
        where={'isUkrainian': True}
    )
    
    print(f"\n🇺🇦 Ukrainian books: {ukrainian:,}")


async def search_operations(db: Prisma):
    """Full-text search and pattern matching."""
    print("\n" + "="*70)
    print("4. SEARCH OPERATIONS")
    print("="*70)
    
    # Search by SKU pattern
    yakaboo_recent = await db.catalogproduct.find_many(
        where={
            'sku': {'startswith': '14'},
            'isbn13': {'not': None}
        },
        take=5,
        order={'createdAt': 'desc'}
    )
    
    print(f"\n🔍 Books with SKU starting with '14':")
    for book in yakaboo_recent:
        print(f"   • {book.isbn13} - SKU: {book.sku}")
    
    # Books with specific notification type
    confirmed = await db.catalogproduct.count(
        where={
            'notificationType': 'NOTIFICATION_CONFIRMED_ON_PUBLICATION'
        }
    )
    print(f"\n✅ Confirmed publications: {confirmed:,}")


async def batch_queries(db: Prisma):
    """Batch operations and transactions."""
    print("\n" + "="*70)
    print("5. BATCH QUERIES")
    print("="*70)
    
    # Find multiple by ISBNs
    isbns = [
        '9789666023998',
        '9786175517987',
        '9786175222294'
    ]
    
    books = await db.catalogproduct.find_many(
        where={
            'isbn13': {'in': isbns}
        }
    )
    
    print(f"\n📦 Batch query for {len(isbns)} ISBNs:")
    for book in books:
        print(f"   ✓ Found: {book.isbn13}")


async def complex_filtering(db: Prisma):
    """Complex WHERE conditions."""
    print("\n" + "="*70)
    print("6. COMPLEX FILTERING")
    print("="*70)
    
    # Multiple AND conditions
    recent_with_isbn = await db.catalogproduct.count(
        where={
            'AND': [
                {'isbn13': {'not': None}},
                {'createdAt': {'gte': datetime(2026, 1, 6)}},
                {'isUkrainian': True}
            ]
        }
    )
    
    print(f"\n📅 Recent Ukrainian books with ISBN: {recent_with_isbn:,}")
    
    # NOT condition
    no_ean = await db.catalogproduct.count(
        where={
            'ean': None
        }
    )
    
    print(f"🔍 Books without EAN: {no_ean:,}")


async def main():
    """Run all examples."""
    db = Prisma()
    await db.connect()
    
    try:
        print("\n" + "="*70)
        print("PRISMA ADVANCED EXAMPLES - YAKABOO COLLECTION")
        print("="*70)
        
        await filtering_and_pagination(db)
        await relations_example(db)
        await aggregations(db)
        await search_operations(db)
        await batch_queries(db)
        await complex_filtering(db)
        
        print("\n" + "="*70)
        print("✅ All examples completed successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
