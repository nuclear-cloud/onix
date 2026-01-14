#!/usr/bin/env python3
"""
Smart Gatekeeper Ingestion Script.
Завантажує сирі дані Yakaboo в RawIngestion таблицю з класифікацією.
"""

import asyncio
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma import Prisma, Json
from prisma.models import RawIngestion
from app.classifiers.isbn_classifier import (
    classify_item,
    extract_isbn_from_record,
    extract_price_from_record,
)
from app.core.prisma_db import prisma as db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


async def process_record(record: dict, source_name: str = "yakaboo") -> Optional[dict]:
    """
    Обробляє один запис з Yakaboo.

    Returns:
        dict для запису в RawIngestion або None якщо пропустити
    """
    # 1. Витягуємо ключі
    source_sku = record.get("sku") or record.get("id")
    if not source_sku:
        return None

    # 2. Знаходимо ISBN/EAN
    barcode = record.get("barcode", "")
    isbn = extract_isbn_from_record(record) or barcode

    # 3. Класифікуємо
    classification = classify_item(isbn)

    # 4. Витягуємо ціну
    price = extract_price_from_record(record)

    # 5. Формуємо payload
    payload = {
        "source": "yakaboo",
        "original": record,
        "classification": classification.to_dict(),
        "price": price,
        "barcode": barcode,
    }

    # 6. Створюємо fingerprint
    raw_line = json.dumps(record, sort_keys=True)
    fingerprint = hashlib.sha256(raw_line.encode("utf-8")).hexdigest()

    return {
        "provider": source_name,
        "source_sku": str(source_sku),
        "isbn": classification.isbn,
        "item_type": classification.item_type.value,
        "status": classification.status.value,
        "payload": payload,
        "fingerprint": fingerprint,
        "price": price if price else None,
        "downloaded_at": datetime.now(timezone.utc),
    }


async def ingest_file(
    file_path: str, limit: Optional[int] = None, batch_size: int = 100
):
    """
    Завантажує дані з JSONL файлу в RawIngestion.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return

    # Підрахунок записів
    total_lines = sum(1 for _ in open(path, "r"))
    limit = min(limit or total_lines, total_lines)

    logger.info(f"Starting ingestion: {limit} records from {file_path}")

    processed = 0
    succeeded = 0
    skipped = 0
    errors = 0

    buffer = []

    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if line_number > limit:
                break

            try:
                record = json.loads(line.strip())
                result = await process_record(record)

                if result is None:
                    skipped += 1
                    processed += 1
                    continue

                buffer.append(result)
                succeeded += 1
                processed += 1

                # Batch insert
                if len(buffer) >= batch_size:
                    await bulk_insert(buffer)
                    buffer.clear()

                    if processed % 1000 == 0:
                        logger.info(
                            f"Progress: {processed}/{limit} ({processed * 100 // limit}%)"
                        )

            except json.JSONDecodeError:
                errors += 1
                skipped += 1
            except Exception as e:
                logger.error(f"Error processing line {line_number}: {e}")
                errors += 1

    # Final insert
    if buffer:
        await bulk_insert(buffer)

    # Summary
    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Total processed: {processed}")
    logger.info(f"  Succeeded:       {succeeded}")
    logger.info(f"  Skipped:         {skipped}")
    logger.info(f"  Errors:          {errors}")
    logger.info("=" * 60)


async def bulk_insert(records: list):
    """Mass insert records into RawIngestion using upsert."""
    for record in records:
        try:
            await db.rawingestion.upsert(
                where={
                    "provider_source_sku": record["provider"],
                    "source_sku": record["source_sku"],
                },
                data={
                    "create": {
                        "provider": record["provider"],
                        "source_sku": record["source_sku"],
                        "isbn": record["isbn"],
                        "item_type": record["item_type"],
                        "status": record["status"],
                        "payload": record["payload"],
                        "fingerprint": record["fingerprint"],
                        "price": record["price"],
                        "downloaded_at": record["downloaded_at"],
                    },
                    "update": {
                        "isbn": record["isbn"],
                        "item_type": record["item_type"],
                        "status": record["status"],
                        "payload": record["payload"],
                        "fingerprint": record["fingerprint"],
                        "price": record["price"],
                        "downloaded_at": record["downloaded_at"],
                    },
                },
            )
        except Exception as e:
            logger.error(f"Upsert error: {e}")


async def show_stats():
    """Показує статистику таблиці."""
    stats = {
        "total": await db.rawingestion.count(),
        "new": await db.rawingestion.count(where={"status": "NEW"}),
        "skipped": await db.rawingestion.count(where={"status": "SKIPPED"}),
        "processed": await db.rawingestion.count(where={"status": "PROCESSED"}),
        "book_ua": await db.rawingestion.count(where={"item_type": "BOOK_UA"}),
        "book_en": await db.rawingestion.count(where={"item_type": "BOOK_EN"}),
        "book_ru": await db.rawingestion.count(where={"item_type": "BOOK_RU"}),
        "merch": await db.rawingestion.count(
            where={"item_type": {"startswith": "MERCH"}}
        ),
    }

    print("\n" + "=" * 60)
    print("RAW INGESTION STATS")
    print("=" * 60)
    print(f"  Total records:    {stats['total']:,}")
    print(f"  NEW (to process): {stats['new']:,}")
    print(f"  SKIPPED:          {stats['skipped']:,}")
    print(f"  PROCESSED:        {stats['processed']:,}")
    print()
    print("  By type:")
    print(f"    BOOK_UA:  {stats['book_ua']:,}")
    print(f"    BOOK_EN:  {stats['book_en']:,}")
    print(f"    BOOK_RU:  {stats['book_ru']:,}")
    print(f"    MERCH:    {stats['merch']:,}")
    print("=" * 60)


async def main():
    import argparse

    # Connect to database
    await db.connect()

    parser = argparse.ArgumentParser(description="Smart Gatekeeper Ingestion")
    parser.add_argument("file", help="Path to JSONL file")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Max records")
    parser.add_argument("--batch", "-b", type=int, default=100, help="Batch size")
    parser.add_argument("--stats", "-s", action="store_true", help="Show stats only")

    args = parser.parse_args()

    try:
        if args.stats:
            await show_stats()
            return

        await ingest_file(args.file, limit=args.limit, batch_size=args.batch)
        await show_stats()
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
