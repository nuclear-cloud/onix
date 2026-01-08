#!/usr/bin/env python3
"""
Приклад використання helper функцій для роботи з українськими книжками
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models import (
    get_ukrainian_products_query,
    get_ukrainian_products,
    count_ukrainian_products,
    Product
)
from sqlalchemy import select, func


async def example_queries():
    """Приклади запитів для українських книжок."""
    
    async with AsyncSessionLocal() as session:
        print("=" * 80)
        print("📚 ПРИКЛАДИ РОБОТИ З УКРАЇНСЬКИМИ КНИЖКАМИ")
        print("=" * 80)
        
        # 1. Підрахунок українських книжок
        print("\n1️⃣ Підрахунок українських книжок")
        print("-" * 80)
        count = await count_ukrainian_products(session)
        print(f"🇺🇦 Всього українських книжок: {count}")
        
        # 2. Отримання перших 10 українських книжок
        print("\n2️⃣ Перші 10 українських книжок")
        print("-" * 80)
        products = await get_ukrainian_products(session, limit=10)
        for i, product in enumerate(products, 1):
            print(f"  {i}. {product.title[:60]}... (ISBN: {product.isbn_13})")
        
        # 3. Використання базового запиту з додатковими фільтрами
        print("\n3️⃣ Пошук українських книжок з фільтрами")
        print("-" * 80)
        
        # Знайти українські книжки з певним видавництвом
        from app.models.product import Publisher
        from sqlalchemy.orm import selectinload
        query = get_ukrainian_products_query()
        query = query.options(selectinload(Product.publisher))
        query = query.join(Product.publisher).where(Publisher.name.ilike('%ліра%'))
        query = query.limit(5)
        
        result = await session.execute(query)
        filtered_products = result.scalars().all()
        print(f"  Знайдено {len(filtered_products)} українських книжок від видавництв з 'ліра' в назві:")
        for product in filtered_products:
            print(f"    - {product.title[:50]}... ({product.publisher.name if product.publisher else 'N/A'})")
        
        # 4. Статистика по форматах українських книжок
        print("\n4️⃣ Статистика по форматах (тільки українські)")
        print("-" * 80)
        query = (
            select(Product.product_form, func.count(Product.id))
            .where(Product.is_ukrainian == True)
            .group_by(Product.product_form)
            .order_by(func.count(Product.id).desc())
            .limit(5)
        )
        result = await session.execute(query)
        for form, count in result.all():
            print(f"  {form or 'NULL'}: {count}")
        
        # 5. Порівняння: всі книжки vs українські
        print("\n5️⃣ Порівняння статистики")
        print("-" * 80)
        
        # Всі книжки
        result = await session.execute(select(func.count(Product.id)))
        total = result.scalar()
        
        # Українські
        ukr_count = await count_ukrainian_products(session)
        
        # Не-українські
        result = await session.execute(
            select(func.count(Product.id)).where(Product.is_ukrainian == False)
        )
        non_ukr = result.scalar()
        
        print(f"  Всього книжок: {total:,}")
        print(f"  Українських: {ukr_count:,} ({ukr_count/total*100:.1f}%)")
        print(f"  Не-українських: {non_ukr:,} ({non_ukr/total*100:.1f}%)")
        
        print("\n" + "=" * 80)
        print("✅ ПРИКЛАДИ ЗАВЕРШЕНО")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(example_queries())

