#!/usr/bin/env python3
"""
Виправлення ONIX compliance для існуючих записів

Оновлює:
1. Додає language до titles
2. Встановлює default мову якщо відсутня
3. Покращує contributors (додає corporate author якщо потрібно)
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.product import Product
from sqlalchemy import select, func, update
from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def fix_onix_json(onix_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Виправляє ONIX JSON для compliance.
    
    Виправлення:
    1. Додає language до titles
    2. Встановлює default мову якщо відсутня
    3. Додає corporate author якщо немає contributors
    """
    fixed = onix_json.copy()
    
    # 1. Визначаємо мову
    lang_code = None
    if "languages" in fixed and isinstance(fixed["languages"], list) and len(fixed["languages"]) > 0:
        lang_code = fixed["languages"][0].get("code")
    
    # Якщо мова не знайдена - визначаємо за назвою
    if not lang_code:
        # Перевіряємо назву на кирилицю
        titles = fixed.get("titles", [])
        if titles and isinstance(titles, list) and len(titles) > 0:
            title_text = titles[0].get("text", "")
            if any('\u0400' <= c <= '\u04FF' for c in title_text):
                lang_code = "ukr"
            else:
                lang_code = "eng"
        else:
            lang_code = "ukr"  # Default
        
        # Додаємо мову
        if "languages" not in fixed:
            fixed["languages"] = []
        fixed["languages"] = [{"role": "01", "code": lang_code}]
    
    # 2. Додаємо language до titles
    if "titles" in fixed and isinstance(fixed["titles"], list):
        for title in fixed["titles"]:
            if isinstance(title, dict) and "language" not in title:
                # Визначаємо мову для title
                if title.get("type") == "03":  # Original title
                    title["language"] = "eng"
                else:
                    title["language"] = lang_code
    
    # 3. Якщо немає contributors - додаємо corporate author з publisher
    if "contributors" not in fixed or not fixed.get("contributors"):
        publishers = fixed.get("publishers", [])
        if publishers and isinstance(publishers, list) and len(publishers) > 0:
            pub_name = publishers[0].get("name")
            if pub_name:
                fixed["contributors"] = [{
                    "role": "B11",  # Research by (corporate)
                    "name": pub_name,
                    "corporate": True,
                }]
    
    return fixed


async def fix_compliance(batch_size: int = 1000, limit: int = None, dry_run: bool = False):
    """
    Виправляє ONIX compliance для всіх записів.
    
    Args:
        batch_size: Розмір батчу для оновлення
        limit: Максимальна кількість записів для оновлення
        dry_run: Якщо True - не зберігає зміни
    """
    
    async with AsyncSessionLocal() as session:
        print("=" * 80)
        print("🔧 ВИПРАВЛЕННЯ ONIX COMPLIANCE")
        print("=" * 80)
        
        if dry_run:
            print("⚠️  DRY RUN MODE - зміни не будуть збережені")
        
        # Загальна кількість
        result = await session.execute(select(func.count(Product.id)))
        total = result.scalar()
        
        print("\n📊 СТАТИСТИКА ДО ВИПРАВЛЕННЯ")
        print("-" * 80)
        print(f"  Всього записів: {total}")
        
        print("\n" + "-" * 80)
        print("🔄 ОНОВЛЕННЯ ЗАПИСІВ...")
        print("-" * 80)
        
        # Обробляємо батчами
        offset = 0
        updated = 0
        errors = 0
        
        while True:
            # Отримуємо батч
            query = select(Product).offset(offset).limit(batch_size)
            if limit:
                remaining = limit - updated
                if remaining <= 0:
                    break
                query = select(Product).offset(offset).limit(min(batch_size, remaining))
            
            result = await session.execute(query)
            products = result.scalars().all()
            
            if not products:
                break
            
            for product in products:
                try:
                    # Виправляємо ONIX JSON
                    fixed_json = fix_onix_json(product.onix_json)
                    
                    # Перевіряємо чи є зміни
                    if fixed_json != product.onix_json:
                        if not dry_run:
                            product.onix_json = fixed_json
                        updated += 1
                except Exception as e:
                    errors += 1
                    logger.warning(f"Помилка при оновленні {product.isbn_13}: {e}")
            
            if not dry_run:
                await session.commit()
            
            offset += batch_size
            
            # Прогрес
            if offset % 10000 == 0:
                print(f"  Оброблено: {offset} / {total} ({offset/total*100:.1f}%)")
        
        print(f"\n✅ Оновлено записів: {updated}")
        print(f"❌ Помилок: {errors}")
        
        # Статистика після
        if not dry_run:
            print("\n📊 СТАТИСТИКА ПІСЛЯ ВИПРАВЛЕННЯ")
            print("-" * 80)
            print(f"  Оновлено записів: {updated}")
        
        print("\n" + "=" * 80)
        print("✅ ВИПРАВЛЕННЯ ЗАВЕРШЕНО")
        print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix ONIX compliance")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size")
    parser.add_argument("--limit", type=int, default=None, help="Limit records")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    asyncio.run(fix_compliance(
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run
    ))

