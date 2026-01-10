"""
Tests for Repository Layer (Prisma).

Unit tests for PrismaProductRepository with mocked Prisma client.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.repositories.prisma_repositories import PrismaProductRepository


def create_mock_product(id: int = 1, isbn13: str = "9786177902421", title: str = "Test Book"):
    """Create a mock CatalogProduct."""
    product = MagicMock()
    product.id = id
    product.isbn13 = isbn13
    product.title = title
    product.subtitle = "Subtitle"
    product.deleted_at = None
    product.created_at = datetime.now()
    product.language_code = "ukr"
    product.publisher_name = "VIVAT"
    product.proprietary_id = f"SKU-{id}"
    product.contributors = []
    product.subjects = []
    product.text_content = []
    product.media_files = []
    product.prices = []
    return product


@pytest.fixture
def mock_db():
    """Create a mock Prisma client."""
    db = AsyncMock()
    db.catalogproduct = AsyncMock()
    return db


@pytest.fixture
def repository(mock_db):
    """Create repository instance with mock DB."""
    return PrismaProductRepository(mock_db)


class TestGetAll:
    """Tests for get_all method."""
    
    @pytest.mark.asyncio
    async def test_get_all_empty(self, repository, mock_db):
        """Test get_all with empty database."""
        mock_db.catalogproduct.count = AsyncMock(return_value=0)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=[])
        
        products, total = await repository.get_all(limit=20, offset=0)
        
        assert total == 0
        assert products == []
        mock_db.catalogproduct.count.assert_called_once()
        mock_db.catalogproduct.find_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_with_products(self, repository, mock_db):
        """Test get_all with products."""
        mock_products = [
            create_mock_product(id=1, title="Book 1"),
            create_mock_product(id=2, title="Book 2"),
        ]
        
        mock_db.catalogproduct.count = AsyncMock(return_value=50)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=mock_products)
        
        products, total = await repository.get_all(limit=2, offset=0)
        
        assert total == 50
        assert len(products) == 2
        assert products[0].title == "Book 1"
    
    @pytest.mark.asyncio
    async def test_get_all_pagination(self, repository, mock_db):
        """Test get_all with pagination."""
        mock_db.catalogproduct.count = AsyncMock(return_value=100)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=[])
        
        await repository.get_all(limit=10, offset=30)
        
        call_kwargs = mock_db.catalogproduct.find_many.call_args[1]
        assert call_kwargs["take"] == 10
        assert call_kwargs["skip"] == 30


class TestGetByIsbn:
    """Tests for get_by_isbn method."""
    
    @pytest.mark.asyncio
    async def test_get_by_isbn_found(self, repository, mock_db):
        """Test get_by_isbn when product exists."""
        mock_product = create_mock_product(isbn13="9786177902421")
        mock_db.catalogproduct.find_unique = AsyncMock(return_value=mock_product)
        
        result = await repository.get_by_isbn("9786177902421")
        
        assert result is not None
        assert result.isbn13 == "9786177902421"
        mock_db.catalogproduct.find_unique.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_isbn_not_found(self, repository, mock_db):
        """Test get_by_isbn when product doesn't exist."""
        mock_db.catalogproduct.find_unique = AsyncMock(return_value=None)
        
        result = await repository.get_by_isbn("9999999999999")
        
        assert result is None


class TestGetBySku:
    """Tests for get_by_sku method."""
    
    @pytest.mark.asyncio
    async def test_get_by_sku_found(self, repository, mock_db):
        """Test get_by_sku when product exists."""
        mock_product = create_mock_product()
        mock_product.proprietary_id = "YAKABOO-12345"
        mock_db.catalogproduct.find_first = AsyncMock(return_value=mock_product)
        
        result = await repository.get_by_sku("YAKABOO-12345")
        
        assert result is not None
        mock_db.catalogproduct.find_first.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_sku_not_found(self, repository, mock_db):
        """Test get_by_sku when product doesn't exist."""
        mock_db.catalogproduct.find_first = AsyncMock(return_value=None)
        
        result = await repository.get_by_sku("NONEXISTENT")
        
        assert result is None


class TestSearch:
    """Tests for search method."""
    
    @pytest.mark.asyncio
    async def test_search_with_results(self, repository, mock_db):
        """Test search with matching products."""
        mock_products = [
            create_mock_product(title="Кобзар"),
            create_mock_product(title="Кобзар 2"),
        ]
        mock_db.catalogproduct.find_many = AsyncMock(return_value=mock_products)
        
        results = await repository.search("Кобзар", limit=20, offset=0)
        
        assert len(results) == 2
        call_kwargs = mock_db.catalogproduct.find_many.call_args[1]
        assert "OR" in call_kwargs["where"]
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, repository, mock_db):
        """Test search with no matching products."""
        mock_db.catalogproduct.find_many = AsyncMock(return_value=[])
        
        results = await repository.search("nonexistent", limit=20, offset=0)
        
        assert results == []


class TestGetUkrainianBooks:
    """Tests for get_ukrainian_books method."""
    
    @pytest.mark.asyncio
    async def test_get_ukrainian_books(self, repository, mock_db):
        """Test getting Ukrainian books only."""
        mock_products = [create_mock_product(id=1)]
        mock_db.catalogproduct.count = AsyncMock(return_value=5000)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=mock_products)
        
        products, total = await repository.get_ukrainian_books(limit=10, offset=0)
        
        assert total == 5000
        assert len(products) == 1
        
        # Verify filter
        count_kwargs = mock_db.catalogproduct.count.call_args[1]
        assert count_kwargs["where"]["language_code"] == "ukr"


class TestGetByPublisher:
    """Tests for get_by_publisher method."""
    
    @pytest.mark.asyncio
    async def test_get_by_publisher(self, repository, mock_db):
        """Test getting books by publisher."""
        mock_products = [
            create_mock_product(id=1, title="VIVAT Book 1"),
            create_mock_product(id=2, title="VIVAT Book 2"),
        ]
        mock_db.catalogproduct.count = AsyncMock(return_value=100)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=mock_products)
        
        products, total = await repository.get_by_publisher("VIVAT", limit=10, offset=0)
        
        assert total == 100
        assert len(products) == 2
        
        # Verify case-insensitive search
        count_kwargs = mock_db.catalogproduct.count.call_args[1]
        assert count_kwargs["where"]["publisher_name"]["mode"] == "insensitive"


class TestIncludeRelations:
    """Tests for proper relation includes."""
    
    @pytest.mark.asyncio
    async def test_get_all_includes_relations(self, repository, mock_db):
        """Verify get_all includes all relations."""
        mock_db.catalogproduct.count = AsyncMock(return_value=0)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=[])
        
        await repository.get_all(limit=10, offset=0)
        
        call_kwargs = mock_db.catalogproduct.find_many.call_args[1]
        includes = call_kwargs["include"]
        
        assert "contributors" in includes
        assert "subjects" in includes
        assert "text_content" in includes
        assert "media_files" in includes
        assert "prices" in includes
    
    @pytest.mark.asyncio
    async def test_get_by_isbn_includes_relations(self, repository, mock_db):
        """Verify get_by_isbn includes all relations."""
        mock_db.catalogproduct.find_unique = AsyncMock(return_value=None)
        
        await repository.get_by_isbn("9786177902421")
        
        call_kwargs = mock_db.catalogproduct.find_unique.call_args[1]
        includes = call_kwargs["include"]
        
        # Should include nested contributor relation
        assert "contributors" in includes
        assert includes["contributors"]["include"]["contributor"] is True
