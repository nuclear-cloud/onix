"""
Tests for PrismaIngestionService raw ingestion archive/idempotency logic.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.prisma_ingestion_service import PrismaIngestionService, PrismaWriter
from app.adapters.data_adapter import BaseDataAdapter
from app.schemas.data_models import ValidationResult, ValidationError


class FakeAdapter(BaseDataAdapter):
    """Minimal adapter stub for testing."""

    def __init__(self):
        super().__init__(source_name="Fake", source_code="FAKE")

    def transform(self, raw_data):
        if raw_data.get("invalid"):
            return ValidationResult.model_construct(
                is_valid=False,
                errors=[ValidationError(field="title", message="Invalid payload")],
            )
        return ValidationResult.model_construct(is_valid=True, data=MagicMock())

    def validate(self, raw_data):
        return ValidationResult(is_valid=True)

    def extract_identifier(self, raw_data):
        return raw_data.get("id")


class MockRawIngestion:
    def __init__(self, find_unique_return=None):
        self.find_unique = AsyncMock(return_value=find_unique_return)
        self.upsert = AsyncMock()
        self.update = AsyncMock()


class MockPrisma:
    def __init__(self, find_unique_return=None):
        self.rawingestion = MockRawIngestion(find_unique_return)
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()


@pytest.mark.asyncio
async def test_skips_already_processed_payload(tmp_path, monkeypatch):
    """Skips import when fingerprint already processed."""

    existing = SimpleNamespace(status="PROCESSED")
    mock_db = MockPrisma(find_unique_return=existing)
    mock_db.is_connected = MagicMock(return_value=True)
    monkeypatch.setattr("app.services.prisma_ingestion_service.shared_db", mock_db)

    raw = {"id": "1", "title": "Test", "isbn": "9781234567890"}
    file_path = tmp_path / "data.jsonl"
    file_path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    adapter = FakeAdapter()
    service = PrismaIngestionService(adapter, batch_size=1)

    metrics = await service.import_from_file(str(file_path))

    assert metrics.skipped == 1
    assert metrics.processed == 1
    assert metrics.succeeded == 0
    assert metrics.failed == 0
    mock_db.rawingestion.find_unique.assert_awaited_once()
    mock_db.rawingestion.upsert.assert_not_awaited()
    mock_db.rawingestion.update.assert_not_awaited()
    mock_db.connect.assert_not_awaited()
    mock_db.disconnect.assert_not_awaited()
