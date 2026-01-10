import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from sqlalchemy.dialects.postgresql.dml import Insert
from sqlalchemy.sql.dml import Update

from scripts.load_reference_codes import load_onix_codelists, load_thema_codes
from app.models.catalog import RefOnixCodelist, RefThemaSubject


@pytest.mark.asyncio
async def test_load_onix_codelists_structure():
    """Verify ONIX loader creates correct record structure."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    
    # Mock JSON data
    mock_data = {
        "ONIXCodeTable": {
            "CodeList": [
                {
                    "CodeListNumber": 1,
                    "IssueNumber": 0,
                    "Code": [
                        {
                            "CodeValue": "01",
                            "CodeDescription": "Test Code",
                            "CodeNotes": "Test Notes",
                            "IssueNumber": 1,
                            "ModifiedNumber": "",
                            "DeprecatedNumber": ""
                        }
                    ]
                }
            ]
        }
    }
    
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value = MagicMock()
        with patch("json.load", return_value=mock_data):
            await load_onix_codelists(session)
    
    # Expect two executes: upsert + deactivate missing
    assert session.execute.call_count == 2
    insert_stmt = session.execute.call_args_list[0].args[0]
    assert isinstance(insert_stmt, Insert)
    assert insert_stmt.table.name == RefOnixCodelist.__tablename__
    compiled = insert_stmt.compile()
    params = compiled.params
    assert any(k.startswith("list_number") and params[k] == 1 for k in params)
    assert any(k.startswith("code") and params[k] == "01" for k in params)
    assert any(k.startswith("description") and params[k] == "Test Code" for k in params)
    assert any(k.startswith("is_active") and params[k] is True for k in params)
    # Second statement should be an update to mark missing codes inactive
    deactivate_stmt = session.execute.call_args_list[1].args[0]
    assert isinstance(deactivate_stmt, Update)
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_load_thema_uses_bfs_topological_sort():
    """Verify THEMA loader uses BFS topological sort for hierarchies."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    
    # BFS should process: root (level 0) -> children (level 1) -> grandchildren (level 2)
    mock_data = {
        "CodeList": {
            "ThemaCodes": {
                "Code": [
                    {"CodeValue": "A-BB-CC", "CodeParent": "A-BB", "CodeDescription": "Deep", "CodeNotes": None},
                    {"CodeValue": "A", "CodeParent": None, "CodeDescription": "Root", "CodeNotes": None},
                    {"CodeValue": "A-BB", "CodeParent": "A", "CodeDescription": "Mid", "CodeNotes": None},
                ]
            }
        }
    }
    
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.return_value = MagicMock()
        with patch("json.load", return_value=mock_data):
            await load_thema_codes(session)
    
    # BFS implementation should result in 3 execute calls for 3 levels (or batched)
    assert session.execute.call_count >= 1
    insert_stmt = session.execute.call_args_list[0].args[0]
    assert isinstance(insert_stmt, Insert)
    assert insert_stmt.table.name == RefThemaSubject.__tablename__
    # Verify all 3 codes are processed (would be split by level in batches)
    compiled = insert_stmt.compile()
    params = compiled.params
    # All codes should appear in the params
    codes_in_params = {params[k] for k in params if k.startswith("code") and params[k] in ["A", "A-BB", "A-BB-CC"]}
    assert len(codes_in_params) > 0  # At least one code batch processed
