"""
Тести для API шарів (Service, Router)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.catalog_service import CatalogService
from app.schemas import ProductCardDTO, CatalogSearchResponseDTO
from app.models import CatalogProduct


@pytest.mark.asyncio
class TestCatalogService:
    """Тести для CatalogService."""
    
    async def test_get_products_list_empty(self):
        """Тест отримання порожнього списку товарів."""
        # Mock session
        session = AsyncMock(spec=AsyncSession)
        
        # Mock repository методу
        with patch('app.services.catalog_service.ProductRepository') as MockRepo:
            mock_repo_instance = AsyncMock()
            MockRepo.return_value = mock_repo_instance
            mock_repo_instance.get_all.return_value = ([], 0)
            
            service = CatalogService(session)
            result = await service.get_products_list(page=1, limit=20)
        
        assert result.total == 0
        assert result.page == 1
        assert result.limit == 20
        assert result.items == []
    
    async def test_get_product_detail_not_found(self):
        """Тест запиту деталі неіснуючого товару."""
        session = AsyncMock(spec=AsyncSession)
        
        with patch('app.services.catalog_service.ProductRepository') as MockRepo:
            mock_repo_instance = AsyncMock()
            MockRepo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.return_value = None
            
            service = CatalogService(session)
            result = await service.get_product_detail("non-existent-id")
        
        assert result is None
    
    async def test_search_empty_results(self):
        """Тест пошуку з порожніми результатами."""
        session = AsyncMock(spec=AsyncSession)
        
        with patch('app.services.catalog_service.ProductRepository') as MockRepo:
            mock_repo_instance = AsyncMock()
            MockRepo.return_value = mock_repo_instance
            mock_repo_instance.search.return_value = ([], 0)
            
            service = CatalogService(session)
            result = await service.search(query="nonexistent", page=1, limit=20)
        
        assert result.total == 0
        assert len(result.items) == 0
        mock_repo_instance.search.assert_called_once()


@pytest.mark.asyncio
class TestCatalogRouter:
    """Тести для API маршрутів."""
    
    @pytest.fixture
    def app_client(self):
        """Створити тестовий FastAPI клієнт."""
        from fastapi.testclient import TestClient
        from main import app
        
        return TestClient(app)
    
    def test_health_check(self, app_client):
        """Тест точки здоров'я."""
        response = app_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_root_endpoint(self, app_client):
        """Тест кореневого ендпоінту."""
        response = app_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ONIX Catalog API"
        assert data["version"] == "1.0.0"
