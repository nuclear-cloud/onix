"""
Catalog Service using Prisma ORM.

Business logic for book catalog operations.
"""

from typing import Optional, List
from prisma import Prisma
from app.repositories.prisma_repositories import PrismaProductRepository


class PrismaCatalogService:
    """Catalog service with Prisma ORM."""
    
    def __init__(self, db: Prisma):
        self.db = db
        self.product_repo = PrismaProductRepository(db)
    
    async def get_catalog(
        self,
        limit: int = 20,
        offset: int = 0,
        ukrainian_only: bool = False,
    ) -> dict:
        """
        Get paginated catalog of books.
        
        Args:
            limit: Items per page
            offset: Pagination offset
            ukrainian_only: Filter for Ukrainian books
        """
        if ukrainian_only:
            products, total = await self.product_repo.get_ukrainian_books(
                limit=limit,
                offset=offset
            )
        else:
            products, total = await self.product_repo.get_all(
                limit=limit,
                offset=offset
            )
        
        return {
            'total': total,
            'limit': limit,
            'offset': offset,
            'items': [self._format_product(p) for p in products],
        }
    
    async def search_books(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Search catalog by title."""
        products = await self.product_repo.search(
            query=query,
            limit=limit,
            offset=offset
        )
        
        return {
            'query': query,
            'count': len(products),
            'items': [self._format_product(p) for p in products],
        }
    
    async def get_book_details(self, isbn13: str) -> Optional[dict]:
        """Get full details for a book."""
        product = await self.product_repo.get_by_isbn(isbn13)
        
        if not product:
            return None
        
        return self._format_product_detailed(product)
    
    async def get_by_publisher(
        self,
        publisher_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Get books by publisher."""
        products, total = await self.product_repo.get_by_publisher(
            publisher_id=publisher_id,
            limit=limit,
            offset=offset
        )
        
        return {
            'publisher_id': publisher_id,
            'total': total,
            'items': [self._format_product(p) for p in products],
        }
    
    async def get_recent_additions(self, limit: int = 20) -> List[dict]:
        """Get recently added books."""
        products = await self.product_repo.get_recent(limit=limit)
        return [self._format_product(p) for p in products]
    
    async def get_statistics(self) -> dict:
        """Get catalog statistics."""
        total = await self.db.catalogproduct.count()
        ukrainian = await self.db.catalogproduct.count(
            where={'isUkrainian': True}
        )
        with_publisher = await self.db.catalogproduct.count(
            where={'publisherId': {'not': None}}
        )
        with_isbn = await self.db.catalogproduct.count(
            where={'isbn13': {'not': None}}
        )
        
        return {
            'total_books': total,
            'ukrainian_books': ukrainian,
            'with_publisher': with_publisher,
            'with_isbn': with_isbn,
            'coverage_isbn': f"{(with_isbn / total * 100):.1f}%" if total > 0 else "0%",
        }
    
    @staticmethod
    def _format_product(product) -> dict:
        """Format product for API response."""
        titles = [t.titleText for t in product.titles] if product.titles else []
        
        return {
            'id': product.id,
            'isbn13': product.isbn13,
            'sku': product.sku,
            'record_reference': product.recordReference,
            'title': titles[0] if titles else 'N/A',
            'product_form': product.productForm,
            'publisher_name': product.publisher.name if product.publisher else None,
            'is_ukrainian': product.isUkrainian,
            'created_at': product.createdAt.isoformat() if product.createdAt else None,
        }
    
    @staticmethod
    def _format_product_detailed(product) -> dict:
        """Format product with full details."""
        titles = [t.titleText for t in product.titles] if product.titles else []
        subjects = []
        if product.subjects:
            subjects = [
                {'code': s.subjectCode, 'heading': s.subjectHeading}
                for s in product.subjects
            ]
        
        languages = []
        if product.languages:
            languages = [l.languageCode for l in product.languages]
        
        return {
            'id': product.id,
            'isbn13': product.isbn13,
            'sku': product.sku,
            'record_reference': product.recordReference,
            'title': titles[0] if titles else 'N/A',
            'titles': titles,
            'product_form': product.productForm,
            'product_form_detail': product.productFormDetail,
            'publisher': {
                'id': product.publisher.id,
                'name': product.publisher.name,
            } if product.publisher else None,
            'edition_number': product.editionNumber,
            'subjects': subjects,
            'languages': languages,
            'is_ukrainian': product.isUkrainian,
            'notification_type': product.notificationType,
            'publishing_status': product.publishingStatus,
            'created_at': product.createdAt.isoformat() if product.createdAt else None,
            'updated_at': product.updatedAt.isoformat() if product.updatedAt else None,
        }
