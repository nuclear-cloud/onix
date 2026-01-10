#!/usr/bin/env python3
"""Quick Prisma verification test."""
import asyncio
from prisma import Prisma

async def test():
    db = Prisma()
    await db.connect()
    total = await db.catalogproduct.count()
    print(f'✅ Prisma working: {total:,} books in database')
    await db.disconnect()

asyncio.run(test())
