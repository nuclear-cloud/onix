import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.catalog_loader import CatalogLoader
from app.models.catalog import RefThemaSubject


@pytest.mark.asyncio
async def test_ensure_thema_cache_loads_once():
    """Verify THEMA cache is loaded only once per loader instance."""
    session = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["AAA", "BBB", "CCC"]
    session.execute.return_value = mock_result
    
    loader = CatalogLoader(session)
    
    # First call loads
    await loader._ensure_thema_cache()
    assert loader._thema_codes == {"AAA", "BBB", "CCC"}
    assert session.execute.call_count == 1
    
    # Second call skips DB query
    await loader._ensure_thema_cache()
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_thema_cache_empty_on_no_refs():
    """Cache should be empty set if no THEMA refs exist."""
    session = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    
    loader = CatalogLoader(session)
    await loader._ensure_thema_cache()
    
    assert loader._thema_codes == set()
