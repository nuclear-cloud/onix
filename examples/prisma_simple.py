#!/usr/bin/env python3
"""
Simple Prisma Example - Query Yakaboo Books

This demonstrates basic Prisma usage with the imported Yakaboo books.
"""

import asyncio
from prisma import Prisma


async def main():
    """Simple queries that work with imported data."""
    
    db = Prisma()
    await db.connect()
    
    try:
        print("=" * 70)
        print("PRISMA CLIENT - YAKABOO BOOKS")
        print("=" * 70)
        
        # 1. Count all products
        total = await db.catalogproduct.count()
        print(f"\n📚 Total books: {total:,}")
        
        # 2. Count books with ISBN
        with_isbn = await db.catalogproduct.count(
            where={'isbn13': {'not': None}}
        )
        print(f"📖 Books with ISBN-13: {with_isbn:,}")
        
        # 3. Get sample books (first 5)
        books = await db.catalogproduct.find_many(
            take=5,
            where={'isbn13': {'not': None}},
            order={'createdAt': 'desc'}
        )
        
        print(f"\n📋 Sample books:")
        for book in books:
            print(f"   • ISBN: {book.isbn13}")
            print(f"     SKU: {book.sku}")
            print(f"     Form: {book.productForm}")
            print(f"     Created: {book.createdAt.strftime('%Y-%m-%d %H:%M')}")
            print()
        
        # 4. Query by specific ISBN
        specific = await db.catalogproduct.find_unique(
            where={'isbn13': '9789666023998'}
        )
        if specific:
            print(f"🔍 Found specific book:")
            print(f"   ISBN: {specific.isbn13}")
            print(f"   SKU: {specific.sku}")
            print(f"   Reference: {specific.recordReference}")
        
        # 5. Search by SKU prefix
        yakaboo_count = await db.catalogproduct.count(
            where={'sku': {'startswith': '2'}}
        )
        print(f"\n🏪 Books with SKU starting with '2': {yakaboo_count:,}")
        
        # 6. Recent imports
        recent = await db.catalogproduct.count(
            where={
                'createdAt': {
                    'gte': '2026-01-06T00:00:00Z'
                }
            }
        )
        print(f"📅 Books imported on 2026-01-06: {recent:,}")
        
        print("\n" + "=" * 70)
        print("✅ Prisma is working correctly!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
