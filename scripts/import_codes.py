#!/usr/bin/env python3
"""
Import THEMA and ONIX codes from CSV files into PostgreSQL database.

Tables created in codelist schema:
- thema_code: 9187 THEMA subject codes with EN/UK descriptions
- onix_code: 4748 ONIX codes from 166 code lists
"""

import asyncio
import csv
from pathlib import Path
from prisma import Prisma


async def import_thema_codes(db: Prisma, csv_path: Path) -> int:
    """Import THEMA codes from CSV."""
    print(f"📖 Loading THEMA codes from {csv_path}...")
    
    codes = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes.append({
                'code': row['code'],
                'description_en': row['description_en'][:500],
                'description_uk': row['description_uk'][:500] if row['description_uk'] else row['description_en'][:500],
                'notes_en': row.get('notes_en') or None,
                'notes_uk': row.get('notes_uk') or None,
                'parent_code': row.get('parent_code') or None,
            })
    
    print(f"   Found {len(codes)} THEMA codes")
    
    # Clear existing data
    await db.execute_raw('DELETE FROM codelist.thema_code')
    
    # Insert in batches (parent codes first to satisfy FK)
    # First pass: codes without parent (root level)
    root_codes = [c for c in codes if not c['parent_code']]
    print(f"   Inserting {len(root_codes)} root codes...")
    
    for code in root_codes:
        await db.themacode.create(data=code)
    
    # Second pass: codes with parent (sorted by code length for hierarchy)
    child_codes = sorted([c for c in codes if c['parent_code']], key=lambda x: len(x['code']))
    print(f"   Inserting {len(child_codes)} child codes...")
    
    batch_size = 500
    for i in range(0, len(child_codes), batch_size):
        batch = child_codes[i:i+batch_size]
        for code in batch:
            try:
                await db.themacode.create(data=code)
            except Exception as e:
                # If parent doesn't exist, insert without parent reference
                code['parent_code'] = None
                await db.themacode.create(data=code)
        print(f"      Processed {min(i+batch_size, len(child_codes))}/{len(child_codes)}")
    
    return len(codes)


async def import_onix_codes(db: Prisma, csv_path: Path) -> int:
    """Import ONIX codes from CSV."""
    print(f"📋 Loading ONIX codes from {csv_path}...")
    
    codes = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes.append({
                'list_number': int(row['list_number']),
                'list_description_en': row['list_description_en'][:200],
                'list_description_uk': row.get('list_description_uk', '')[:200] or None,
                'code': row['code'][:50],
                'description_en': row['description_en'][:500],
                'description_uk': row.get('description_uk', '')[:500] or None,
                'notes': row.get('notes') or None,
            })
    
    print(f"   Found {len(codes)} ONIX codes")
    
    # Clear existing data
    await db.execute_raw('DELETE FROM codelist.onix_code')
    
    # Insert in batches
    batch_size = 500
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i+batch_size]
        await db.onixcode.create_many(data=batch)
        print(f"   Processed {min(i+batch_size, len(codes))}/{len(codes)}")
    
    return len(codes)


async def main():
    """Main import function."""
    print("=" * 60)
    print("ONIX Aggregator - Code Import Script")
    print("=" * 60)
    
    # Paths
    base_path = Path(__file__).parent.parent
    thema_csv = base_path / 'data' / 'thema_codes.csv'
    onix_csv = base_path / 'data' / 'onix_codes.csv'
    
    # Check files exist
    if not thema_csv.exists():
        print(f"❌ THEMA CSV not found: {thema_csv}")
        return
    if not onix_csv.exists():
        print(f"❌ ONIX CSV not found: {onix_csv}")
        return
    
    # Connect to database
    db = Prisma()
    await db.connect()
    
    try:
        # Import THEMA
        thema_count = await import_thema_codes(db, thema_csv)
        print(f"✅ Imported {thema_count} THEMA codes\n")
        
        # Import ONIX
        onix_count = await import_onix_codes(db, onix_csv)
        print(f"✅ Imported {onix_count} ONIX codes\n")
        
        print("=" * 60)
        print(f"📊 SUMMARY:")
        print(f"   THEMA codes: {thema_count}")
        print(f"   ONIX codes:  {onix_count}")
        print("=" * 60)
        
    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
