"""
Import complete Thema v1.6 Ukrainian classification from JSON.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parents[1]))

from app.core.database import AsyncSessionLocal
from app.models.catalog import RefThemaSubject

THEMA_FILE = "data/thema_v1.6_uk.json"

async def seed_thema_full():
    if not os.path.exists(THEMA_FILE):
        print(f"Error: {THEMA_FILE} not found!")
        return

    with open(THEMA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    codes = data.get("CodeList", {}).get("ThemaCodes", {}).get("Code", [])
    
    async with AsyncSessionLocal() as session:
        print(f"Start importing {len(codes)} Thema codes...")
        
        # Batch processing to avoid overhead
        batch_size = 500
        count = 0
        
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i+batch_size]
            for item in batch:
                code_val = str(item.get("CodeValue"))
                parent_val = str(item.get("CodeParent")) if item.get("CodeParent") else None
                
                obj = RefThemaSubject(
                    code=code_val,
                    parent_code=parent_val,
                    label_uk=item.get("CodeDescription"),
                    label_en=item.get("CodeDescription"), # Fallback if we don't have EN here
                    description_uk=item.get("CodeNotes")
                )
                await session.merge(obj)
                count += 1
            
            await session.flush()
            print(f"Processed {count}/{len(codes)} codes...")
        
        await session.commit()
        print(f"Successfully imported {count} Thema categories with Ukrainian localization.")

if __name__ == "__main__":
    asyncio.run(seed_thema_full())