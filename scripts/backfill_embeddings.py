#!/usr/bin/env python3
"""
Backfill embeddings for CatalogProduct using pgvector/pgai or OpenAI fallback.

Usage:
  python scripts/backfill_embeddings.py --limit 10000
  python scripts/backfill_embeddings.py --resume --batch 500

Env:
  OPENAI_API_KEY (optional, used if pgai is not available)
  OPENAI_EMBEDDING_MODEL (default: text-embedding-3-small)
"""
import asyncio
import argparse
from datetime import datetime

from prisma import Prisma
from app.services.embedding_service import ensure_extensions, embed_product


async def run(limit: int | None, batch: int, resume: bool) -> None:
    db = Prisma()
    await db.connect()
    try:
        await ensure_extensions(db)
        where = {"embedding": {"equals": None}} if resume else {}
        total = await db.catalogproduct.count(where=where)
        print(f"Found {total:,} products to process.")
        processed = 0
        cursor = None
        while True:
            take = batch
            if limit is not None:
                remaining = max(0, limit - processed)
                if remaining <= 0:
                    break
                take = min(take, remaining)
            items = await db.catalogproduct.find_many(
                where=where,
                take=take,
                cursor={"id": cursor} if cursor else None,
                skip=1 if cursor else 0,
                order={"id": "asc"},
            )
            if not items:
                break
            for it in items:
                ok = await embed_product(db, it.id)
                processed += 1
                if processed % 100 == 0:
                    print(f"{datetime.now().isoformat()} processed: {processed:,}")
            cursor = items[-1].id
        print(f"Done. Processed {processed:,} products.")
    finally:
        await db.disconnect()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch", type=int, default=500)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args.limit, args.batch, args.resume))


if __name__ == "__main__":
    main()
