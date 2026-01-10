#!/usr/bin/env python3
"""
Inspect catalog products and show a merged/side-by-side view of normalized vs denormalized fields.

Usage:
  python scripts/inspect_catalog_sample.py --limit 20 --offset 0 > review_sample.jsonl

Output: JSONL lines with keys:
  id, isbn13, sku
  normalized: {title, publisher, languages, subjects, contributors}
  denormalized: {title, subtitle, publisherName, language, description, mainSubject, thematicCategory}

This is read-only and meant for human review/approval.
"""
import argparse
import asyncio
import json
from typing import List

from prisma import Prisma


async def fetch_sample(limit: int, offset: int) -> List[dict]:
    db = Prisma()
    await db.connect()
    try:
        products = await db.catalogproduct.find_many(
            take=limit,
            skip=offset,
            order={"id": "asc"},
            include={
                "titles": True,
                "publisher": True,
                "languages": True,
                "subjects": True,
                "catalog_product_contributors_link": {
                    "include": {"catalog_contributors": True}
                },
            },
        )
        result = []
        for p in products:
            title_norm = None
            subtitle_norm = None
            if p.titles:
                title_norm = p.titles[0].titleText
                subtitle_norm = p.titles[0].subtitle
            publisher_norm = p.publisher.name if p.publisher else None
            languages_norm = [lng.code for lng in p.languages] if p.languages else []
            subjects_norm = []
            if p.subjects:
                for s in p.subjects:
                    subjects_norm.append(s.subject_heading_text or s.subjectCode)
            contributors_norm = []
            if p.catalog_product_contributors_link:
                for link in p.catalog_product_contributors_link:
                    if link.catalog_contributors:
                        contributors_norm.append(link.catalog_contributors.name)
            result.append(
                {
                    "id": p.id,
                    "isbn13": p.isbn13,
                    "sku": p.sku,
                    "normalized": {
                        "title": title_norm,
                        "subtitle": subtitle_norm,
                        "publisher": publisher_norm,
                        "languages": languages_norm,
                        "subjects": subjects_norm,
                        "contributors": contributors_norm,
                    },
                    "denormalized": {
                        "title": p.title,
                        "subtitle": p.subtitle,
                        "publisherName": p.publisherName,
                        "language": p.language,
                        "description": p.description,
                        "shortDescription": p.shortDescription,
                        "mainSubject": p.mainSubject,
                        "thematicCategory": p.thematicCategory,
                    },
                }
            )
        return result
    finally:
        await db.disconnect()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--offset", type=int, default=0)
    args = ap.parse_args()
    rows = asyncio.run(fetch_sample(args.limit, args.offset))
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
