#!/usr/bin/env python3
"""
Ініціалізація бази даних

Створює таблиці та індекси для збереження ONIX+ даних.
"""

import asyncio
import sys
from pathlib import Path

# Додаємо корінь проекту до шляху
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine, Base
from app.models import Product, Publisher, Author, Collection, ProductAuthor


async def init_database():
    """Створює всі таблиці в базі даних."""
    print("🗄️  Ініціалізація бази даних...")
    
    async with engine.begin() as conn:
        # Видаляємо всі таблиці якщо вони існують
        print("🗑️  Видалення старих таблиць...")
        await conn.run_sync(Base.metadata.drop_all)
        
        # Створюємо всі таблиці
        print("📦 Створення таблиць...")
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ База даних ініціалізована!")
    print("\nСтворені таблиці:")
    print("  - products")
    print("  - publishers")
    print("  - authors")
    print("  - collections")
    print("  - product_authors")


if __name__ == "__main__":
    asyncio.run(init_database())






