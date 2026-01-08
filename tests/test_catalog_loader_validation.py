import pytest
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.services.catalog_loader import CatalogLoader
from app.models.codes_v71 import SubjectSchemeIdentifier
from app.models.catalog import CatalogSubject


@pytest.mark.asyncio
async def test_process_subjects_skips_invalid_thema():
    session = AsyncMock()
    session.add = MagicMock()
    loader = CatalogLoader(session)
    loader._thema_codes = {"AAA"}

    pid = uuid4()
    valid = SimpleNamespace(subject_scheme_identifier="93", subject_code="AAA", subject_heading_text=None)
    invalid = SimpleNamespace(subject_scheme_identifier="93", subject_code="ZZZ", subject_heading_text=None)
    onix = SimpleNamespace(subject=[valid, invalid])

    await loader._process_subjects(pid, onix)

    # Should add only the valid THEMA subject
    assert session.add.call_count == 1
    added: CatalogSubject = session.add.call_args[0][0]
    assert isinstance(added, CatalogSubject)
    assert added.subject_code == "AAA"


@pytest.mark.asyncio
async def test_process_subjects_allows_non_thema():
    session = AsyncMock()
    session.add = MagicMock()
    loader = CatalogLoader(session)
    loader._thema_codes = set()

    pid = uuid4()
    non_thema = SimpleNamespace(subject_scheme_identifier=SubjectSchemeIdentifier.PROPRIETARY_SUBJECT_SCHEME, subject_code="ABC", subject_heading_text="Heading")
    onix = SimpleNamespace(subject=[non_thema])

    await loader._process_subjects(pid, onix)

    assert session.add.call_count == 1
    added: CatalogSubject = session.add.call_args[0][0]
    assert added.subject_code == "ABC"
    assert added.subject_heading_text == "Heading"
