"""
Tests for API layers (Service, Router) - Prisma Edition

Tests for Prisma-based catalog service and router.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from prisma import Prisma

from app.services.prisma_catalog_service import PrismaCatalogService
from app.core.prisma_db import get_db
from app.core.config import settings


@pytest.mark.asyncio
class TestPrismaCatalogService:
    """Tests for PrismaCatalogService with Prisma."""
    
    async def test_service_initialization(self):
        """Test service initialization."""
        mock_db = AsyncMock(spec=Prisma)
        service = PrismaCatalogService(mock_db)
        
        assert service is not None
        assert service.db == mock_db
        assert hasattr(service, 'product_repo')
    
    async def test_service_has_methods(self):
        """Test that service has required methods."""
        mock_db = AsyncMock(spec=Prisma)
        service = PrismaCatalogService(mock_db)
        
        # Verify all required methods exist
        assert hasattr(service, 'get_catalog')
        assert hasattr(service, 'search_books')
        assert hasattr(service, 'get_book_details')
        assert hasattr(service, 'get_by_publisher')
        assert hasattr(service, 'get_recent_additions')
        assert hasattr(service, 'get_statistics')


class TestConfiguration:
    """Tests for Prisma configuration."""
    
    def test_prisma_database_url_configured(self):
        """Test that Prisma database URL is properly configured."""
        assert hasattr(settings, 'PRISMA_DATABASE_URL')
        # In test environment, this should be set
        assert settings.PRISMA_DATABASE_URL is not None or settings.PRISMA_DATABASE_URL == ""
    
    def test_settings_can_be_loaded(self):
        """Test that settings can be properly loaded."""
        from app.core.config import Settings
        assert Settings is not None

