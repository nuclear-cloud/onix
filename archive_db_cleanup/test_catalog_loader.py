"""
Simple test to verify CatalogLoader and MarketLoader services work.
Tests are integration-focused using mocks, not pure unit tests.
"""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.services.catalog_loader import CatalogLoader
from app.services.market_loader import MarketLoader


@pytest.mark.asyncio
async def test_catalog_loader_instantiation():
    """Test that CatalogLoader can be instantiated with a session."""
    mock_session = AsyncMock()
    loader = CatalogLoader(mock_session)
    
    assert loader is not None
    assert loader.session is mock_session
    assert hasattr(loader, 'load_product')
    assert hasattr(loader, '_extract_id')
    assert hasattr(loader, '_find_product')


@pytest.mark.asyncio
async def test_market_loader_instantiation():
    """Test that MarketLoader can be instantiated with a session."""
    mock_session = AsyncMock()
    loader = MarketLoader(mock_session)
    
    assert loader is not None
    assert loader.session is mock_session
    assert hasattr(loader, 'update_price')
