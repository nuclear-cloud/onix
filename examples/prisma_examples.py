#!/usr/bin/env python3
"""
Example: Using Prisma Client with ONIX Database

This demonstrates how to use Prisma alongside SQLAlchemy in the same project.
Prisma provides a modern, type-safe ORM with excellent autocomplete support.
"""

import asyncio
from prisma import Prisma
from typing import Optional, List


async def example_queries():
    """Demonstrate various Prisma queries."""
    
    # Initialize Prisma client
    db = Prisma()
    await db.connect()
    
    try:
        print("🔍 Prisma Client Examples\n")
        
        # 1. Count all products
        total = await db.catalogproduct.count()
        print(f"📚 Total books in database: {total:,}")
        
        # 2. Find products by ISBN
        product = await db.catalogproduct.find_first(
            where={'isbn13': '9789666023998'}
        )
        if product:
            print(f"\n📖 Found book:")
            print(f"   ISBN: {product.isbn13}")
            print(f"   SKU: {product.sku}")
            print(f"   Form: {product.productForm}")
        
        # 3. Get recent books (last 10)
        recent = await db.catalogproduct.find_many(
            take=10,
            order={'createdAt': 'desc'},
            where={'isbn13': {'not': None}}
        )
        print(f"\n📅 Recent books ({len(recent)}):")
        for book in recent[:5]:
            print(f"   - {book.isbn13}: {book.sku}")
        
        # 4. Count by product form
        books = await db.catalogproduct.count(
            where={'productForm': 'BB'}
        )
        print(f"\n📚 Hardback books (BB): {books:,}")
        
        # 5. Filter Ukrainian books
        ukrainian = await db.catalogproduct.count(
            where={'isUkrainian': True}
        )
        print(f"🇺🇦 Ukrainian books: {ukrainian:,}")
        
        # 6. Search by SKU pattern
        yakaboo_books = await db.catalogproduct.count(
            where={'sku': {'startswith': '1'}}
        )
        print(f"🏪 Books with SKU starting with '1': {yakaboo_books:,}")
        
        # 7. Group query - publishers with products
        publishers = await db.publisher.find_many(
            take=5,
            include={'products': True}
        )
        print(f"\n🏢 Publishers with books:")
        for pub in publishers:
            print(f"   - {pub.name}: {len(pub.products)} books")
        
        # 8. Complex where clause
        specific_books = await db.catalogproduct.find_many(
            where={
                'AND': [
                    {'isbn13': {'not': None}},
                    {'productForm': 'BB'},
                    {'isUkrainian': True}
                ]
            },
            take=5
        )
        print(f"\n🎯 Ukrainian hardback books with ISBN: {len(specific_books)}")
        
        # 9. Pagination
        page_1 = await db.catalogproduct.find_many(
            skip=0,
            take=100,
            where={'isbn13': {'not': None}}
        )
        print(f"\n📄 Page 1: {len(page_1)} books")
        
        # 10. Update example (commented out for safety)
        # updated = await db.catalogproduct.update(
        #     where={'isbn13': '9789666023998'},
        #     data={'isUkrainian': True}
        # )
        
    finally:
        await db.disconnect()
    
    print("\n✅ Done!")


async def create_book_example():
    """Example: Create a new book (commented for safety)."""
    db = Prisma()
    await db.connect()
    
    try:
        # Uncomment to create a test book
        # new_book = await db.catalogproduct.create(
        #     data={
        #         'recordReference': 'test-book-001',
        #         'isbn13': '9780000000001',
        #         'sku': 'TEST-001',
        #         'productForm': 'BB',
        #         'isUkrainian': True
        #     }
        # )
        # print(f"Created book: {new_book.isbn13}")
        pass
    finally:
        await db.disconnect()


async def bulk_operations():
    """Example: Bulk operations with Prisma."""
    db = Prisma()
    await db.connect()
    
    try:
        # Bulk create (commented for safety)
        # books = await db.catalogproduct.create_many(
        #     data=[
        #         {'recordReference': 'bulk-1', 'isbn13': '9780000000002', 'sku': 'BULK-1', 'productForm': 'BB'},
        #         {'recordReference': 'bulk-2', 'isbn13': '9780000000003', 'sku': 'BULK-2', 'productForm': 'BB'},
        #     ]
        # )
        # print(f"Created {books} books")
        
        # Bulk update
        # updated = await db.catalogproduct.update_many(
        #     where={'sku': {'startswith': 'BULK-'}},
        #     data={'isUkrainian': True}
        # )
        # print(f"Updated {updated} books")
        
        # Bulk delete (BE CAREFUL!)
        # deleted = await db.catalogproduct.delete_many(
        #     where={'sku': {'startswith': 'TEST-'}}
        # )
        # print(f"Deleted {deleted} books")
        
        pass
    finally:
        await db.disconnect()


async def relations_example():
    """Example: Working with relations."""
    db = Prisma()
    await db.connect()
    
    try:
        # Get product with all relations
        product = await db.catalogproduct.find_first(
            where={'isbn13': {'not': None}},
            include={
                'publisher': True,
                'titles': True,
                'contributors': True,
                'subjects': True,
                'languages': True
            }
        )
        
        if product:
            print(f"\n📖 Book with relations:")
            print(f"   ISBN: {product.isbn13}")
            
            if product.publisher:
                print(f"   Publisher: {product.publisher.name}")
            
            if product.titles:
                print(f"   Titles: {len(product.titles)}")
            
            if product.contributors:
                print(f"   Contributors: {len(product.contributors)}")
            
            if product.subjects:
                print(f"   Subjects: {len(product.subjects)}")
            
            if product.languages:
                print(f"   Languages: {len(product.languages)}")
    
    finally:
        await db.disconnect()


if __name__ == '__main__':
    print("=" * 70)
    print("PRISMA CLIENT EXAMPLES FOR ONIX PROJECT")
    print("=" * 70)
    
    # Run examples
    asyncio.run(example_queries())
    
    # Uncomment to run other examples:
    # asyncio.run(relations_example())
    # asyncio.run(bulk_operations())
