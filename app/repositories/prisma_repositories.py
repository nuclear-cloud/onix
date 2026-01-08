"""
Prisma-based Repository Layer.

Direct Prisma client queries with type safety.
"""

from typing import Optional, List
from prisma import Prisma
from prisma.models import CatalogProduct, CatalogTitle


class PrismaProductRepository:
    """All book access through Prisma ORM."""
    
    def __init__(self, db: Prisma):
        self.db = db
    
    async def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[CatalogProduct], int]:
        """
        Get all active products with pagination.
        
        Returns:
            (list of products, total count)
        """
        # Total count
        total = await self.db.catalogproduct.count()
        
        # Paginated list with relations
        products = await self.db.catalogproduct.find_many(
            take=limit,
            skip=offset,
            include={
                'titles': True,
                'subjects': True,
                'publisher': True,
                'extents': True,
                'measures': True,
                'languages': True,
            },
            order={'createdAt': 'desc'}
        )
        
        return (products, total)
    
    async def get_by_isbn(self, isbn13: str) -> Optional[CatalogProduct]:
        """Get product by ISBN-13."""
        return await self.db.catalogproduct.find_unique(
            where={'isbn13': isbn13},
            include={
                'titles': True,
                'subjects': True,
                'publisher': True,
                'extents': True,
                'measures': True,
                'languages': True,
                'contributors': True,
                'texts': True,
            }
        )
    
    async def get_by_sku(self, sku: str) -> Optional[CatalogProduct]:
        """Get product by SKU."""
        return await self.db.catalogproduct.find_first(
            where={'sku': sku},
            include={
                'titles': True,
                'subjects': True,
                'publisher': True,
            }
        )
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CatalogProduct]:
        """
        Full-text search across titles.
        
        Args:
            query: Search term
            limit: Max results
            offset: Pagination offset
        """
        # Search in titles
        products = await self.db.catalogproduct.find_many(
            where={
                'titles': {
                    'some': {
                        'titleText': {'contains': query}
                    }
                }
            },
            take=limit,
            skip=offset,
            include={'titles': True, 'publisher': True}
        )
        return products
    
    async def get_ukrainian_books(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[CatalogProduct], int]:
        """Get only Ukrainian books."""
        total = await self.db.catalogproduct.count(
            where={'isUkrainian': True}
        )
        
        books = await self.db.catalogproduct.find_many(
            where={'isUkrainian': True},
            take=limit,
            skip=offset,
            include={'titles': True, 'publisher': True},
            order={'createdAt': 'desc'}
        )
        
        return (books, total)
    
    async def get_by_publisher(
        self,
        publisher_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[CatalogProduct], int]:
        """Get all books by a publisher."""
        total = await self.db.catalogproduct.count(
            where={'publisherId': publisher_id}
        )
        
        books = await self.db.catalogproduct.find_many(
            where={'publisherId': publisher_id},
            take=limit,
            skip=offset,
            include={'titles': True, 'publisher': True},
            order={'createdAt': 'desc'}
        )
        
        return (books, total)
    
    async def get_recent(
        self,
        limit: int = 20,
    ) -> List[CatalogProduct]:
        """Get recently added books."""
        return await self.db.catalogproduct.find_many(
            take=limit,
            order={'createdAt': 'desc'},
            include={'titles': True, 'publisher': True}
        )
    
    async def count_by_form(self) -> dict:
        """Count books by product form (HARDBACK, PAPERBACK, etc)."""
        # Group by productForm using aggregation
        counts = {}
        
        # Get unique forms
        products = await self.db.catalogproduct.find_many(
            select={'productForm': True},
            distinct=['productForm']
        )
        
        for product in products:
            form = product.productForm
            count = await self.db.catalogproduct.count(
                where={'productForm': form}
            )
            counts[form] = count
        
        return counts
    
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
    """Publisher repository using Prisma."""
    
    def __init__(self, db: Prisma):
        self.db = db
    
    async def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List, int]:
        """Get all publishers."""
        total = await self.db.publisher.count()
        
        publishers = await self.db.publisher.find_many(
            take=limit,
            skip=offset,
            include={'products': True},
            order={'name': 'asc'}
        )
        
        return (publishers, total)
    
    async def get_by_id(self, publisher_id: str):
        """Get publisher by ID."""
        return await self.db.publisher.find_unique(
            where={'id': publisher_id},
            include={'products': True}
        )
    
    async def search(self, query: str, limit: int = 20) -> List:
        """Search publishers by name."""
        return await self.db.publisher.find_many(
            where={'name': {'contains': query}},
            take=limit,
            include={'products': True},
            order={'name': 'asc'}
        )
