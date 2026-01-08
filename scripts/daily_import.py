#!/usr/bin/env python3
"""
ШЛЯХ 1: Щоденний Повний Імпорт Каталогу (Daily Catalog Import)

Що робить:
- Завантажує повний список продуктів від Yakaboo
- Парсить всі поля (описи, зображення, характеристики)
- Створює нові продукти або оновлює існуючі
- Виконується 1 раз на добу (вночі)

Запуск:
    python scripts/daily_import.py
    python scripts/daily_import.py --source yakaboo --limit 1000
"""
import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import argparse

# Додаємо project root до Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.product_service import ProductService
from app.adapters.yakaboo import YakabooAdapter


async def load_yakaboo_catalog_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Завантажує каталог з файлу (для тестування).
    В продакшні тут буде API запит до Yakaboo.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.endswith('.jsonl'):
            # JSONL format (one JSON per line)
            return [json.loads(line) for line in f if line.strip()]
        else:
            # Regular JSON array
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'items' in data:
                return data['items']
            else:
                return [data]


async def fetch_yakaboo_catalog_from_api(
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Завантажує каталог з Yakaboo API (production mode).
    
    TODO: Реалізувати справжній API клієнт
    """
    # PLACEHOLDER: В реальності тут буде HTTP запит
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     response = await client.get("https://yakaboo.ua/api/products")
    #     return response.json()['items']
    
    print("⚠️  API fetch not implemented yet. Use --file option.")
    return []


async def run_daily_import(
    source: str = "yakaboo",
    file_path: Optional[str] = None,
    limit: Optional[int] = None,
    batch_size: int = 100
):
    """
    Головна функція щоденного імпорту.
    
    Args:
        source: Джерело даних (yakaboo, ksd, vivat)
        file_path: Шлях до файлу з даними (для тестування)
        limit: Обмеження кількості продуктів
        batch_size: Розмір пакету для обробки
    """
    print("="*70)
    print("🌅 DAILY CATALOG IMPORT (FULL MODE)")
    print("="*70)
    print(f"Source: {source}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Batch size: {batch_size}")
    print("="*70)
    
    # 1. Завантаження даних
    if file_path:
        print(f"📁 Loading from file: {file_path}")
        raw_products = await load_yakaboo_catalog_from_file(file_path)
    else:
        print(f"🌐 Fetching from API...")
        raw_products = await fetch_yakaboo_catalog_from_api(limit)
    
    if limit:
        raw_products = raw_products[:limit]
    
    print(f"📊 Loaded {len(raw_products)} products")
    
    if not raw_products:
        print("❌ No products to import")
        return
    
    # 2. Ініціалізація сервісів
    async for session in get_db():
        service = ProductService(session)
        adapter = YakabooAdapter()
        
        # 3. Запуск імпорту
        try:
            stats = await service.import_full_batch(
                raw_products=raw_products,
                adapter=adapter,
                batch_size=batch_size
            )
            
            # 4. Фінальний звіт
            print("\n" + "="*70)
            print("📈 IMPORT RESULTS")
            print("="*70)
            print(f"✅ Created: {stats['created']}")
            print(f"🔄 Updated: {stats['updated']}")
            print(f"❌ Errors: {stats['errors']}")
            print(f"⏭️  Skipped: {stats['skipped']}")
            print(f"📊 Total: {sum(stats.values())}")
            print("="*70)
            
            # Adapter stats
            adapter_stats = adapter.get_stats()
            print(f"📦 Adapter stats: {adapter_stats}")
            print("="*70)
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
        finally:
            await session.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Daily Full Catalog Import"
    )
    parser.add_argument(
        '--source',
        default='yakaboo',
        choices=['yakaboo', 'ksd', 'vivat'],
        help='Data source'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Path to JSON/JSONL file with products'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of products to import'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for processing'
    )
    
    args = parser.parse_args()
    
    # Запуск
    asyncio.run(run_daily_import(
        source=args.source,
        file_path=args.file,
        limit=args.limit,
        batch_size=args.batch_size
    ))


if __name__ == "__main__":
    main()
