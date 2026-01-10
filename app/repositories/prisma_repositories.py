"""
Prisma-based Repository Layer.

Direct Prisma client queries with type safety.
"""

from typing import Optional, List, Tuple
from prisma import Prisma
from prisma.models import CatalogProduct


class PrismaProductRepository:
    """All book access through Prisma ORM."""
    
    def __init__(self, db: Prisma):
        self.db = db
    
    async def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[CatalogProduct], int]:
        """
        Get all active products with pagination.
        
        Returns:
            (list of products, total count)
        """
        total = await self.db.catalogproduct.count(
            where={'deleted_at': None}
        )
        
        products = await self.db.catalogproduct.find_many(
            take=limit,
            skip=offset,
            where={'deleted_at': None},
            include={
                'contributors': {'include': {'contributor': True}},
                'subjects': {'include': {'subject': True}},
                'text_content': True,
                'media_files': True,
                'prices': True,
            },
            order={'created_at': 'desc'}
        )
        
        return (products, total)
    
    async def get_by_isbn(self, isbn13: str) -> Optional[CatalogProduct]:
        """Get product by ISBN-13."""
        return await self.db.catalogproduct.find_unique(
            where={'isbn13': isbn13},
            include={
                'contributors': {'include': {'contributor': True}},
                'subjects': {'include': {'subject': True}},
                'text_content': True,
                'media_files': True,
                'prices': True,
            }
        )
    
    async def get_by_sku(self, sku: str) -> Optional[CatalogProduct]:
        """Get product by proprietary ID."""
        return await self.db.catalogproduct.find_first(
            where={'proprietary_id': sku},
            include={
                'contributors': {'include': {'contributor': True}},
                'subjects': {'include': {'subject': True}},
            }
        )
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CatalogProduct]:
        """
        Full-text search across title and subtitle.
        
        Args:
            query: Search term
            limit: Max results
            offset: Pagination offset
        """
        products = await self.db.catalogproduct.find_many(
            where={
                'deleted_at': None,
                'OR': [
                    {'title': {'contains': query, 'mode': 'insensitive'}},
                    {'subtitle': {'contains': query, 'mode': 'insensitive'}},
                ]
            },
            take=limit,
            skip=offset,
            include={
                'contributors': {'include': {'contributor': True}},
            },
            order={'created_at': 'desc'}
        )
        return products
    
    async def get_ukrainian_books(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[CatalogProduct], int]:
        """Get only Ukrainian books."""
        where = {
            'language_code': 'ukr',
            'deleted_at': None,
        }
        
        total = await self.db.catalogproduct.count(where=where)
        
        books = await self.db.catalogproduct.find_many(
            where=where,
            take=limit,
            skip=offset,
            include={
                'contributors': {'include': {'contributor': True}},
            },
            order={'created_at': 'desc'}
        )
        
        return (books, total)
    
    async def get_by_publisher(
        self,
        publisher_name: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[CatalogProduct], int]:
        """Get all books by a publisher."""
        where = {
            'publisher_name': {'contains': publisher_name, 'mode': 'insensitive'},
            'deleted_at': None,
        }
        
        total = await self.db.catalogproduct.count(where=where)
        
        books = await self.db.catalogproduct.find_many(
            where=where,
            take=limit,
            skip=offset,
            order={'created_at': 'desc'}
        )
        
        return (books, total)
    
    async def get_recent(
        self,
        limit: int = 20,
    ) -> List[CatalogProduct]:
        """Get recently added books."""
        return await self.db.catalogproduct.find_many(
            where={'deleted_at': None},
            take=limit,
            order={'created_at': 'desc'},
            include={
                'contributors': {'include': {'contributor': True}},
            }
        )
    
    async def count_by_form(self) -> dict:
        """Count books by product form (BB=Hardback, BC=Paperback, etc)."""
        counts = {}
        
        # Get unique forms
        forms = await self.db.catalogproduct.find_many(
            select={'product_form_code': True},
            distinct=['product_form_code'],
            where={'deleted_at': None}
        )
        
        for product in forms:
            form = product.product_form_code
            count = await self.db.catalogproduct.count(
                where={'product_form_code': form, 'deleted_at': None}
            )
            counts[form] = count
        
        return counts
    
    async def get_statistics(self) -> dict:
        """Get catalog statistics."""
        total_products = await self.db.catalogproduct.count(
            where={'deleted_at': None}
        )
        total_contributors = await self.db.contributor.count()
        total_subjects = await self.db.subject.count()
        
        return {
            'total_products': total_products,
            'total_contributors': total_contributors,
            'total_subjects': total_subjects,
        }
    
    async def create(self, data: dict) -> CatalogProduct:
        """Create new product."""
        return await self.db.catalogproduct.create(data=data)
    
    async def update(self, isbn13: str, data: dict) -> Optional[CatalogProduct]:
        """Update product by ISBN-13."""
        return await self.db.catalogproduct.update(
            where={'isbn13': isbn13},
            data=data
        )
    
    async def delete(self, isbn13: str) -> bool:
        """Delete product by ISBN-13."""
        result = await self.db.catalogproduct.delete(
            where={'isbn13': isbn13}
        )
        return result is not None


class PrismaPublisherRepository:
    """Publisher stats using Prisma (no separate Publisher table)."""
    
    def __init__(self, db: Prisma):
        self.db = db
    
    async def get_top_publishers(self, limit: int = 20) -> List[dict]:
        """Get top publishers by book count."""
        # Use raw query for aggregation
        result = await self.db.query_raw(
            """
            SELECT publisher_name, COUNT(*) as book_count
            FROM catalog_products
            WHERE publisher_name IS NOT NULL AND deleted_at IS NULL
            GROUP BY publisher_name
            ORDER BY book_count DESC
            LIMIT $1
            """,
            limit
        )
        return result
    
    async def search(self, query: str, limit: int = 20) -> List[dict]:
        """Search publishers by name."""
        result = await self.db.query_raw(
            """
            SELECT DISTINCT publisher_name, COUNT(*) as book_count
            FROM catalog_products
            WHERE publisher_name ILIKE $1 AND deleted_at IS NULL
            GROUP BY publisher_name
            ORDER BY book_count DESC
            LIMIT $2
            """,
            f'%{query}%',
            limit
        )
        return result
