"""
Integration Tests for Catalog Router.

Tests FastAPI endpoints with mocked Prisma client using FastAPI's dependency_overrides.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime
from decimal import Decimal

from app.routers.catalog import router
from app.core.prisma_db import get_db


def create_mock_product(
    id: int = 1,
    isbn13: str = "9786177902421",
    title: str = "Test Book",
    subtitle: str = "Test Subtitle",
    language_code: str = "ukr",
    publisher_name: str = "VIVAT",
) -> MagicMock:
    """Create a mock CatalogProduct."""
    product = MagicMock()
    product.id = id
    product.isbn13 = isbn13
    product.isbn10 = None
    product.title = title
    product.subtitle = subtitle
    product.language_code = language_code
    product.publisher_name = publisher_name
    product.publication_date = datetime(2024, 1, 15)
    product.product_form_code = "BB"
    product.page_count = 256
    product.deleted_at = None
    product.created_at = datetime.now()
    
    # Relations
    product.contributors = []
    product.subjects = []
    product.text_content = []
    product.media_files = []
    product.prices = []
    product.sales_rights = []
    product.related_products_from = []
    product.related_products_to = []
    
    return product


def create_mock_contributor(
    role_code: str = "A01",
    person_name: str = "Тарас Шевченко",
    sequence: int = 1,
) -> MagicMock:
    """Create a mock Contributor."""
    contrib = MagicMock()
    contrib.role_code = role_code
    contrib.contributor_type = "person"
    contrib.person_name = person_name
    contrib.corporate_name = None
    contrib.sequence_number = sequence
    return contrib


def create_mock_subject(
    scheme_code: str = "93",
    subject_code: str = "FBA",
    heading: str = "Сучасна проза",
) -> MagicMock:
    """Create a mock Subject."""
    subject = MagicMock()
    subject.scheme_code = scheme_code
    subject.subject_code = subject_code
    subject.subject_heading_text = heading
    return subject


class TestPaginationValidation:
    """Tests for query parameter validation."""
    
    def test_limit_validation_max(self):
        """Test limit max validation (100)."""
        app = FastAPI()
        app.include_router(router)
        
        # Override db dependency
        mock_db = AsyncMock()
        mock_db.catalogproduct.count = AsyncMock(return_value=0)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=[])
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        response = client.get("/catalog/products?limit=200")
        
        # Should fail validation - limit max is 100
        assert response.status_code == 422
    
    def test_page_validation_min(self):
        """Test page min validation (>= 1)."""
        app = FastAPI()
        app.include_router(router)
        
        mock_db = AsyncMock()
        mock_db.catalogproduct.count = AsyncMock(return_value=0)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=[])
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        response = client.get("/catalog/products?page=0")
        
        # Should fail validation - page >= 1
        assert response.status_code == 422


class TestSearchValidation:
    """Tests for search endpoint validation."""
    
    def test_search_query_required(self):
        """Test search requires query parameter."""
        app = FastAPI()
        app.include_router(router)
        
        mock_db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        response = client.get("/catalog/search")
        
        # Should fail - q is required
        assert response.status_code == 422
    
    def test_search_query_min_length(self):
        """Test search query minimum length."""
        app = FastAPI()
        app.include_router(router)
        
        mock_db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        response = client.get("/catalog/search?q=a")
        
        # Should fail - min_length is 2
        assert response.status_code == 422


class TestProductDetailResponseFormat:
    """Tests for product detail response format."""
    
    def test_product_detail_response_structure(self):
        """Test product detail includes expected fields."""
        app = FastAPI()
        app.include_router(router)
        
        product = create_mock_product()
        product.contributors = [create_mock_contributor()]
        product.subjects = [create_mock_subject()]
        
        mock_db = AsyncMock()
        mock_db.catalogproduct.find_unique = AsyncMock(return_value=product)
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        response = client.get("/catalog/products/9786177902421")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected fields
        assert "id" in data
        assert "isbn13" in data
        assert "title" in data
        assert "contributors" in data
        assert "subjects" in data
        assert data["isbn13"] == "9786177902421"
        assert data["title"] == "Test Book"
        assert len(data["contributors"]) == 1


class TestProductNotFound:
    """Tests for 404 responses."""
    
    def test_product_not_found_returns_404(self):
        """Test 404 for non-existent product."""
        app = FastAPI()
        app.include_router(router)
        
        mock_db = AsyncMock()
        mock_db.catalogproduct.find_unique = AsyncMock(return_value=None)
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        response = client.get("/catalog/products/0000000000000")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListProductsResponse:
    """Tests for list products response format."""
    
    def test_list_products_response_structure(self):
        """Test list products returns correct structure."""
        app = FastAPI()
        app.include_router(router)
        
        products = [
            create_mock_product(id=1, isbn13="978111", title="Book 1"),
            create_mock_product(id=2, isbn13="978222", title="Book 2"),
        ]
        
        mock_db = AsyncMock()
        mock_db.catalogproduct.count = AsyncMock(return_value=50)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=products)
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        response = client.get("/catalog/products?page=1&limit=20")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "items" in data
        assert data["total"] == 50
        assert data["page"] == 1
        assert data["limit"] == 20
        assert len(data["items"]) == 2
    
    def test_list_products_empty(self):
        """Test list products returns empty list when no data."""
        app = FastAPI()
        app.include_router(router)
        
        mock_db = AsyncMock()
        mock_db.catalogproduct.count = AsyncMock(return_value=0)
        mock_db.catalogproduct.find_many = AsyncMock(return_value=[])
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        response = client.get("/catalog/products")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestSearchResponse:
    """Tests for search endpoint response format."""
    
    def test_search_response_structure(self):
        """Test search returns correct structure."""
        app = FastAPI()
        app.include_router(router)
        
        products = [create_mock_product(title="Кобзар")]
        
        mock_db = AsyncMock()
        mock_db.catalogproduct.find_many = AsyncMock(return_value=products)
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        response = client.get("/catalog/search?q=Кобзар")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query" in data
        assert "items" in data
        assert data["query"] == "Кобзар"
        assert len(data["items"]) == 1
