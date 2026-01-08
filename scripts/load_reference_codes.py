import asyncio
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Set, Tuple

from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal, engine
from app.models import RefOnixCodelist, RefThemaSubject

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ONIX_PATH = DATA_DIR / "ONIX_BookProduct_Codelists_Issue_71.json"
THEMA_PATH = DATA_DIR / "thema_v1.6_uk.json"


async def load_onix_codelists(session):
    with ONIX_PATH.open() as f:
        data = json.load(f)

    code_lists = data.get("ONIXCodeTable", {}).get("CodeList", [])
    records: List[dict] = []

    for code_list in code_lists:
        list_number = int(code_list["CodeListNumber"])
        base_issue = str(code_list.get("IssueNumber", "") or "")
        for code in code_list.get("Code", []):
            records.append(
                {
                    "list_number": list_number,
                    "code": str(code.get("CodeValue")),
                    "description": code.get("CodeDescription"),
                    "notes": code.get("CodeNotes"),
                    "issue_number": str(code.get("IssueNumber", base_issue) or base_issue or ""),
                    "modified_number": str(code.get("ModifiedNumber", "") or ""),
                    "deprecated_number": str(code.get("DeprecatedNumber", "") or ""),
                    "is_active": True,
                }
            )

    if not records:
        await session.execute(RefOnixCodelist.__table__.update().values(is_active=False))
        await session.commit()
        print("Loaded 0 ONIX codelist entries (all marked inactive)")
        return

    # Batch insert (PostgreSQL has ~65k param limit, 7 cols × 1000 rows = 7k params)
    BATCH_SIZE = 1000
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        stmt = insert(RefOnixCodelist).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=[RefOnixCodelist.list_number, RefOnixCodelist.code],
            set_={
                "description": stmt.excluded.description,
                "notes": stmt.excluded.notes,
                "issue_number": stmt.excluded.issue_number,
                "modified_number": stmt.excluded.modified_number,
                "deprecated_number": stmt.excluded.deprecated_number,
                "is_active": True,
            },
        )
        await session.execute(stmt)
        print(f"  Batch {i // BATCH_SIZE + 1}: {len(batch)} records")

    incoming_keys: Set[Tuple[int, str]] = {(r["list_number"], r["code"]) for r in records}
    await session.execute(
        RefOnixCodelist.__table__.update()
        .where(tuple_(RefOnixCodelist.list_number, RefOnixCodelist.code).notin_(incoming_keys))
        .values(is_active=False)
    )

    await session.commit()
    print(f"✅ Upserted {len(records)} ONIX codelist entries from {ONIX_PATH.name}")


async def load_thema_codes(session):
    """Load THEMA codes with topological ordering using BFS to handle multi-level hierarchy."""
    with THEMA_PATH.open() as f:
        data = json.load(f)

    thema_codes = data.get("CodeList", {}).get("ThemaCodes", {}).get("Code", [])
    
    # Step 1: Build code_to_record map and parent→children map
    code_to_record: Dict[str, dict] = {}
    parent_to_children: Dict[str, List[str]] = defaultdict(list)
    roots: Set[str] = set()

    for code in thema_codes:
        code_value = str(code.get("CodeValue", ""))
        parent_code_raw = code.get("CodeParent")
        parent_code = str(parent_code_raw) if parent_code_raw is not None and str(parent_code_raw).strip() else None
        label = str(code.get("CodeDescription", ""))
        notes = str(code.get("CodeNotes", ""))
        
        record = {
            "code": code_value,
            "parent_code": parent_code,
            "label_en": label,
            "label_uk": label,
            "description_en": notes,
            "description_uk": notes,
            "is_active": True,
        }
        code_to_record[code_value] = record
        
        if parent_code is None or parent_code == code_value:
            roots.add(code_value)
        else:
            parent_to_children[parent_code].append(code_value)

    if not code_to_record:
        await session.execute(RefThemaSubject.__table__.update().values(is_active=False))
        await session.commit()
        print("Loaded 0 THEMA codes (all marked inactive)")
        return

    # Step 2: BFS to determine levels
    levels: Dict[str, int] = {}
    queue: deque = deque()

    for root in roots:
        levels[root] = 0
        queue.append(root)

    while queue:
        current_code = queue.popleft()
        current_level = levels[current_code]

        for child in parent_to_children.get(current_code, []):
            if child not in levels:
                levels[child] = current_level + 1
                queue.append(child)

    # Step 3: Check for orphaned codes (codes with parents that don't exist)
    orphaned = set(code_to_record.keys()) - set(levels.keys())
    if orphaned:
        print(f"⚠️  Warning: {len(orphaned)} orphaned codes (parent not found):")
        for orphan_code in sorted(list(orphaned)[:10]):  # Show first 10
            parent = code_to_record[orphan_code]["parent_code"]
            print(f"   - {orphan_code} → parent: {parent}")
        if len(orphaned) > 10:
            print(f"   ... and {len(orphaned) - 10} more")

    # Step 4: Group records by level
    records_by_level: Dict[int, List[dict]] = defaultdict(list)
    for code_value, level in levels.items():
        records_by_level[level].append(code_to_record[code_value])

    max_level = max(levels.values()) if levels else -1
    print(f"Loading {len(levels)} THEMA codes across {max_level + 1} levels")

    BATCH_SIZE = 1000
    
    # Step 5: Insert level by level
    for level in range(max_level + 1):
        level_records = records_by_level[level]
        if not level_records:
            continue
            
        print(f"  Level {level}: {len(level_records)} codes")
        
        for i in range(0, len(level_records), BATCH_SIZE):
            batch = level_records[i : i + BATCH_SIZE]
            stmt = insert(RefThemaSubject).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[RefThemaSubject.code],
                set_={
                    "parent_code": stmt.excluded.parent_code,
                    "label_en": stmt.excluded.label_en,
                    "label_uk": stmt.excluded.label_uk,
                    "description_en": stmt.excluded.description_en,
                    "description_uk": stmt.excluded.description_uk,
                    "is_active": True,
                },
            )
            await session.execute(stmt)
            if len(level_records) > BATCH_SIZE:
                print(f"    Batch {i // BATCH_SIZE + 1}: {len(batch)} records")

    # Step 6: Mark codes not in incoming data as inactive
    incoming_codes: Set[str] = set(code_to_record.keys())
    await session.execute(
        RefThemaSubject.__table__.update()
        .where(RefThemaSubject.code.notin_(incoming_codes))
        .values(is_active=False)
    )

    await session.commit()
    print(f"✅ Upserted {len(code_to_record)} THEMA codes from {THEMA_PATH.name}")


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(RefOnixCodelist.__table__.create, checkfirst=True)
        await conn.run_sync(RefThemaSubject.__table__.create, checkfirst=True)

    async with AsyncSessionLocal() as session:
        try:
            await load_onix_codelists(session)
            await load_thema_codes(session)
        except IntegrityError as exc:
            await session.rollback()
            raise SystemExit(f"Failed to load reference codes: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
