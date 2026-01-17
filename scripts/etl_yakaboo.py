#!/usr/bin/env python3
"""
ETL Script for Yakaboo Data Import with Price Delta Tracking.
Imports into cold.RawIngestion (current state) and cold.PriceHistory (price changes).
"""

import json
import hashlib
import logging
import os
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
    """Create database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "onix_db"),
        user=os.getenv("DB_USER", "onix_user"),
        password=os.getenv("DB_PASS"),
    )


def process_record(record: dict, source: str = "yakaboo") -> dict:
    """
    Process a single record from Yakaboo data.
    """
    barcode = record.get("barcode", "")
    classification = classify_item(barcode)
    price = extract_price_from_record(record)
    external_id = str(record.get("id", ""))

    # Generate fingerprint for deduplication (check if ANYTHING changed)
    raw_line = json.dumps(record, sort_keys=True)
    fingerprint = hashlib.sha256(raw_line.encode("utf-8")).hexdigest()

    payload = {
        "source": source,
        "original": record,
        "classification": classification.to_dict(),
        "price": price,
    }

    return {
        "source": source,
        "external_id": external_id,
        "code": classification.code,
        "item_type": classification.item_type.value,
        "status": classification.status.value,
        "payload": payload,
        "fingerprint": fingerprint,
        "price": price,
        "downloaded_at": datetime.now(timezone.utc),
    }


def batch_insert(cur, records: list) -> tuple[int, int, int]:
    """
    Insert a batch of records using Delta Price logic.
    Returns: (inserted_new, updated_price, updated_timestamp)
    """
    if not records:
        return 0, 0, 0

    inserted = 0
    updated_price = 0
    updated_ts = 0

    # 1. Deduplicate by external_id within the batch (take last one)
    batch_map = {r["external_id"]: r for r in records}
    external_ids = list(batch_map.keys())

    # 2. Get current state from DB for these IDs
    cur.execute(
        """
        SELECT external_id, price, fingerprint 
        FROM cold."RawIngestion" 
        WHERE source = %s AND external_id = ANY(%s)
    """,
        (records[0]["source"], external_ids),
    )

    db_state = {
        row[0]: {
            "price": float(row[1]) if row[1] is not None else None,
            "fingerprint": row[2],
        }
        for row in cur.fetchall()
    }

    for ext_id, r in batch_map.items():
        new_price = float(r["price"]) if r["price"] is not None else None
        new_fingerprint = r["fingerprint"]

        if ext_id not in db_state:
            # BRAND NEW ITEM
            cur.execute(
                """
                INSERT INTO cold."RawIngestion" 
                (source, external_id, code, item_type, status, payload, fingerprint, price, downloaded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    r["source"],
                    r["external_id"],
                    r["code"],
                    r["item_type"],
                    r["status"],
                    json.dumps(r["payload"]),
                    r["fingerprint"],
                    r["price"],
                    r["downloaded_at"],
                ),
            )

            # Record initial price in history
            if new_price is not None:
                cur.execute(
                    """
                    INSERT INTO cold."PriceHistory" (external_id, code, price, source, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    (
                        r["external_id"],
                        r["code"],
                        r["price"],
                        r["source"],
                        r["downloaded_at"],
                    ),
                )

            inserted += 1

        else:
            old_state = db_state[ext_id]

            if old_state["fingerprint"] == new_fingerprint:
                # NOTHING CHANGED
                cur.execute(
                    """
                    UPDATE cold."RawIngestion" SET downloaded_at = %s 
                    WHERE source = %s AND external_id = %s
                """,
                    (r["downloaded_at"], r["source"], r["external_id"]),
                )
                updated_ts += 1
            else:
                # SOMETHING CHANGED
                cur.execute(
                    """
                    UPDATE cold."RawIngestion" 
                    SET code=%s, item_type=%s, status=%s, payload=%s, fingerprint=%s, price=%s, downloaded_at=%s
                    WHERE source=%s AND external_id=%s
                """,
                    (
                        r["code"],
                        r["item_type"],
                        r["status"],
                        json.dumps(r["payload"]),
                        r["fingerprint"],
                        r["price"],
                        r["downloaded_at"],
                        r["source"],
                        r["external_id"],
                    ),
                )

                # If price changed, record in history
                if new_price != old_state["price"] and new_price is not None:
                    cur.execute(
                        """
                        INSERT INTO cold."PriceHistory" (external_id, code, price, source, timestamp)
                        VALUES (%s, %s, %s, %s, %s)
                    """,
                        (
                            r["external_id"],
                            r["code"],
                            r["price"],
                            r["source"],
                            r["downloaded_at"],
                        ),
                    )
                    updated_price += 1
                else:
                    updated_ts += 1

    return inserted, updated_price, updated_ts


def import_data(file_path: str, limit: Optional[int] = None, batch_size: int = 500):
    path = Path(file_path)
    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return

    # Estimated total lines for progress
    logger.info(f"Scanning file: {file_path}")
    total_lines = limit if limit else sum(1 for _ in open(path, "r"))

    logger.info(f"Starting ETL: {total_lines} records from {file_path}")

    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    stats = {
        "processed": 0,
        "inserted": 0,
        "updated_price": 0,
        "updated_ts": 0,
        "errors": 0,
    }
    buffer = []

    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if limit and line_number > limit:
                break

            try:
                record = json.loads(line.strip())
                result = process_record(record)
                buffer.append(result)
                stats["processed"] += 1

                if len(buffer) >= batch_size:
                    i, up, ut = batch_insert(cur, buffer)
                    stats["inserted"] += i
                    stats["updated_price"] += up
                    stats["updated_ts"] += ut
                    buffer.clear()

                    if stats["processed"] % 5000 == 0:
                        logger.info(
                            f"Progress: {stats['processed']}/{total_lines} (Ins: {stats['inserted']}, PrcUp: {stats['updated_price']})"
                        )

            except Exception as e:
                logger.error(f"Error processing line {line_number}: {e}")
                stats["errors"] += 1

    if buffer:
        i, up, ut = batch_insert(cur, buffer)
        stats["inserted"] += i
        stats["updated_price"] += up
        stats["updated_ts"] += ut

    cur.close()
    conn.close()

    print()
    print("=" * 70)
    print("ETL COMPLETE")
    print("=" * 70)
    print(f"  Processed:      {stats['processed']:,}")
    print(f"  New Items:      {stats['inserted']:,}")
    print(f"  Price Changes:  {stats['updated_price']:,}")
    print(f"  Unchanged:      {stats['updated_ts']:,}")
    print(f"  Errors:         {stats['errors']:,}")
    print("=" * 70)


def show_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM cold."RawIngestion"')
    total_ri = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM cold."PriceHistory"')
    total_ph = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(
        f"\nDB Stats:\n  RawIngestion: {total_ri:,} records\n  PriceHistory: {total_ph:,} records"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="JSONL file")
    parser.add_argument("--limit", "-l", type=int)
    parser.add_argument("--batch", "-b", type=int, default=500)
    parser.add_argument("--stats", "-s", action="store_true")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        import_data(args.file, limit=args.limit, batch_size=args.batch)
        show_stats()
