#!/usr/bin/env python3
"""
ETL Script for Yakaboo Data Import.
Imports from data/yakaboo_complete_final.jsonl into cold.RawIngestion table.
Records all data including incomplete, no duplicates.
"""

import json
import hashlib
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from app.classifiers.isbn_classifier import classify_item, extract_price_from_record

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(
        host="localhost",
        database="onix_db",
        user="onix_user",
        password="onix_secure_pass_2024",
    )


def process_record(record: dict, source: str = "yakaboo") -> dict:
    """
    Process a single record from Yakaboo data.

    Returns:
        dict with fields for RawIngestion table
    """
    # Get barcode/code
    barcode = record.get("barcode", "")

    # Classify the item
    classification = classify_item(barcode)

    # Get price
    price = extract_price_from_record(record)

    # Generate fingerprint for deduplication
    raw_line = json.dumps(record, sort_keys=True)
    fingerprint = hashlib.sha256(raw_line.encode("utf-8")).hexdigest()

    # Build payload with original data + classification
    payload = {
        "source": source,
        "original": record,
        "classification": classification.to_dict(),
        "price": price,
    }

    return {
        "source": source,
        "code": classification.code,
        "item_type": classification.item_type.value,
        "status": classification.status.value,
        "payload": payload,
        "fingerprint": fingerprint,
        "price": price,
        "downloaded_at": datetime.now(timezone.utc),
    }


def import_data(file_path: str, limit: Optional[int] = None, batch_size: int = 1000):
    """
    Import data from JSONL file into RawIngestion table.

    Args:
        file_path: Path to JSONL file
        limit: Maximum number of records to process (None = all)
        batch_size: Batch size for database inserts
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return

    # Count total lines
    total_lines = sum(1 for _ in open(path, "r"))
    limit = min(limit or total_lines, total_lines)

    logger.info(f"Starting ETL: {limit} records from {file_path}")

    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    stats = {
        "processed": 0,
        "inserted": 0,
        "duplicates": 0,
        "errors": 0,
        "NEW": 0,
        "NOCODE": 0,
        "BOOK_UA": 0,
        "BOOK_EN": 0,
        "BOOK_RU": 0,
        "MERCH": 0,
    }

    buffer = []

    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if line_number > limit:
                break

            try:
                record = json.loads(line.strip())
                result = process_record(record)

                buffer.append(result)
                stats["processed"] += 1

                # Batch insert
                if len(buffer) >= batch_size:
                    inserted, duplicates = batch_insert(cur, buffer)
                    stats["inserted"] += inserted
                    stats["duplicates"] += duplicates
                    buffer.clear()

                    if stats["processed"] % 10000 == 0:
                        logger.info(
                            f"Progress: {stats['processed']}/{limit} ({stats['processed'] * 100 // limit}%)"
                        )

            except json.JSONDecodeError:
                stats["errors"] += 1
            except Exception as e:
                logger.error(f"Error processing line {line_number}: {e}")
                stats["errors"] += 1

    # Final insert
    if buffer:
        inserted, duplicates = batch_insert(cur, buffer)
        stats["inserted"] += inserted
        stats["duplicates"] += duplicates

    # Count by type
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'NEW') as new_status,
            COUNT(*) FILTER (WHERE status = 'NOCODE') as nocode_status,
            COUNT(*) FILTER (WHERE item_type = 'BOOK_UA') as book_ua,
            COUNT(*) FILTER (WHERE item_type = 'BOOK_EN') as book_en,
            COUNT(*) FILTER (WHERE item_type = 'BOOK_RU') as book_ru,
            COUNT(*) FILTER (WHERE item_type IN ('MERCH_UA', 'MERCH_CN', 'MERCH_OTHER')) as merch
        FROM cold."RawIngestion"
    """)
    row = cur.fetchone()

    cur.close()
    conn.close()

    # Print summary
    print()
    print("=" * 70)
    print("ETL COMPLETE")
    print("=" * 70)
    print(f"  File:           {file_path}")
    print(f"  Processed:      {stats['processed']:,}")
    print(f"  Inserted:       {stats['inserted']:,}")
    print(f"  Duplicates:     {stats['duplicates']:,}")
    print(f"  Errors:         {stats['errors']:,}")
    print()
    print("  Current table stats:")
    print(f"    Total records:     {row[0]:,}")
    print(f"    NEW status:        {row[1]:,}")
    print(f"    NOCODE:            {row[2]:,}")
    print(f"    BOOK_UA:           {row[3]:,}")
    print(f"    BOOK_EN:           {row[4]:,}")
    print(f"    BOOK_RU:           {row[5]:,}")
    print(f"    MERCH:             {row[6]:,}")
    print("=" * 70)


def batch_insert(cur, records: list) -> tuple[int, int]:
    """
    Insert a batch of records using UPSERT (no duplicates).

    Returns:
        tuple of (inserted_count, duplicate_count)
    """
    inserted = 0
    duplicates = 0

    for record in records:
        try:
            cur.execute(
                """
                INSERT INTO cold."RawIngestion" 
                (source, code, item_type, status, payload, fingerprint, price, downloaded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fingerprint) DO NOTHING
            """,
                (
                    record["source"],
                    record["code"],
                    record["item_type"],
                    record["status"],
                    json.dumps(record["payload"]),
                    record["fingerprint"],
                    record["price"],
                    record["downloaded_at"],
                ),
            )

            if cur.rowcount > 0:
                inserted += 1
            else:
                duplicates += 1

        except Exception as e:
            logger.error(f"Insert error: {e}")

    return inserted, duplicates


def show_stats():
    """Show current table statistics."""
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'NEW') as new_status,
            COUNT(*) FILTER (WHERE status = 'NOCODE') as nocode_status,
            COUNT(*) FILTER (WHERE item_type = 'BOOK_UA') as book_ua,
            COUNT(*) FILTER (WHERE item_type = 'BOOK_EN') as book_en,
            COUNT(*) FILTER (WHERE item_type = 'BOOK_RU') as book_ru,
            COUNT(*) FILTER (WHERE item_type IN ('MERCH_UA', 'MERCH_CN', 'MERCH_OTHER')) as merch
        FROM cold."RawIngestion"
    """)
    row = cur.fetchone()

    cur.close()
    conn.close()

    print()
    print("=" * 70)
    print("RAW INGESTION STATS")
    print("=" * 70)
    print(f"  Total records:     {row[0]:,}")
    print(f"  NEW status:        {row[1]:,}")
    print(f"  NOCODE:            {row[2]:,}")
    print()
    print("  By type:")
    print(f"    BOOK_UA:         {row[3]:,}")
    print(f"    BOOK_EN:         {row[4]:,}")
    print(f"    BOOK_RU:         {row[5]:,}")
    print(f"    MERCH:           {row[6]:,}")
    print("=" * 70)


def show_samples(limit: int = 5):
    """Show sample records from the table."""
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, source, code, item_type, status, 
               payload->'original'->>'name' as name,
               payload->'original'->>'sku' as sku,
               downloaded_at
        FROM cold."RawIngestion"
        ORDER BY downloaded_at DESC
        LIMIT %s
    """,
        (limit,),
    )

    print()
    print("=" * 70)
    print("SAMPLE RECORDS")
    print("=" * 70)
    print(f"{'code':<15} {'item_type':<12} {'status':<8} {'name':<40}")
    print("-" * 75)

    for row in cur.fetchall():
        name = (
            (row[5][:37] + "...") if row[5] and len(row[5]) > 40 else (row[5] or "N/A")
        )
        print(f"{row[2] or 'None':<15} {row[3]:<12} {row[4]:<8} {name}")

    print("=" * 70)

    cur.close()
    conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Yakaboo ETL Import")
    parser.add_argument(
        "file",
        nargs="?",
        default="data/yakaboo_complete_final.jsonl",
        help="Path to JSONL file (default: data/yakaboo_complete_final.jsonl)",
    )
    parser.add_argument("--limit", "-l", type=int, default=None, help="Max records")
    parser.add_argument("--batch", "-b", type=int, default=1000, help="Batch size")
    parser.add_argument("--stats", "-s", action="store_true", help="Show stats only")
    parser.add_argument("--samples", "-S", type=int, metavar="N", help="Show N samples")

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.samples:
        show_samples(args.samples)
        return

    import_data(args.file, limit=args.limit, batch_size=args.batch)
    show_stats()


if __name__ == "__main__":
    main()
