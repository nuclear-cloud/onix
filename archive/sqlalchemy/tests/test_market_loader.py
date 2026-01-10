import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.market_loader import MarketLoader
from app.models.market import Supplier

@pytest.mark.asyncio
async def test_market_loader_update_price():
    """Test that MarketLoader correctly constructs INSERT/UPDATE queries."""
    
    # Mock Session
    mock_session = AsyncMock()
    
    # Mock result for get_supplier_id (assume supplier exists)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Supplier(id=uuid4(), code="yakaboo")
    mock_session.execute.return_value = mock_result
    
    # Mock result for insert returning ID
    mock_insert_result = MagicMock()
    mock_insert_result.scalar_one.return_value = uuid4() # Offer ID
    
    # Setup execute sequence
    # 1. Select Supplier -> returns Supplier
    # 2. Insert/Update Offer -> returns Offer ID
    mock_session.execute.side_effect = [mock_result, mock_insert_result]

    loader = MarketLoader(mock_session)
    
    book_id = uuid4()
    await loader.update_price(
        book_id=book_id,
        supplier_code="yakaboo",
        sku="123",
        price=100.0,
        url="http://test",
        in_stock=True
    )
    
    # Assertions
    assert mock_session.execute.call_count == 2
    # Verify History was added
    assert mock_session.add.call_count == 1 
    added_obj = mock_session.add.call_args[0][0]
    assert added_obj.__tablename__ == "price_history"
    assert added_obj.price == 100.0
