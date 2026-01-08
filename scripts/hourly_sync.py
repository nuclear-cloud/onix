#!/usr/bin/env python3
"""
ШЛЯХ 2: Погодинна Синхронізація Маркет-Даних (Hourly Market Sync)

Що робить:
- Завантажує тільки ціни та наявність від Yakaboo
- Швидко оновлює існуючі продукти
- НЕ створює нові продукти (тільки оновлює)
- Виконується кожну годину

Запуск:
    python scripts/hourly_sync.py
    python scripts/hourly_sync.py --source yakaboo --limit 5000
"""
import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse

# Додаємо project root до Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.product_service import ProductService
from app.adapters.yakaboo import YakabooAdapter


async def load_market_data_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Завантажує маркет-дані з файлу (для тестування).
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.endswith('.jsonl'):
            return [json.loads(line) for line in f if line.strip()]
        else:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'items' in data:
                return data['items']
            else:
                return [data]


async def fetch_market_data_from_api(
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Завантажує маркет-дані з Yakaboo API (production mode).
    
    В реальності тут буде легкий API endpoint який повертає
    тільки SKU, ціни та наявність (без описів і зображень).
    
    TODO: Реалізувати справжній API клієнт
    """
    # PLACEHOLDER
    print("⚠️  API fetch not implemented yet. Use --file option.")
    return []


async def run_hourly_sync(
    source: str = "yakaboo",
    file_path: Optional[str] = None,
    limit: Optional[int] = None,
    batch_size: int = 500  # Більший батч для швидкої операції
):
    """
    Головна функція погодинної синхронізації.
    
    Args:
        source: Джерело даних
        file_path: Шлях до файлу (для тестування)
        limit: Обмеження кількості
        batch_size: Розмір пакету
    """
    print("="*70)
    print("⚡ HOURLY MARKET SYNC (FAST MODE)")
    print("="*70)
    print(f"Source: {source}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Batch size: {batch_size}")
    print("="*70)
    
    # 1. Завантаження даних
    if file_path:
        print(f"📁 Loading from file: {file_path}")
        raw_products = await load_market_data_from_file(file_path)
    else:
        print(f"🌐 Fetching from API...")
        raw_products = await fetch_market_data_from_api(limit)
    
    if limit:
        raw_products = raw_products[:limit]
    
    print(f"📊 Loaded {len(raw_products)} products")
    
    if not raw_products:
        print("❌ No products to sync")
        return
    
    # 2. Ініціалізація сервісів
    async for session in get_db():
        service = ProductService(session)
        adapter = YakabooAdapter()
        
        # 3. Запуск синхронізації
        try:
            result = await service.update_market_batch(
                raw_products=raw_products,
                adapter=adapter,
                batch_size=batch_size
            )
            
            # 4. Фінальний звіт
            print("\n" + "="*70)
            print("📈 SYNC RESULTS")
            print("="*70)
            print(f"📦 Total processed: {result.total}")
            print(f"🔄 Updated: {result.updated}")
            print(f"➕ Created: {result.created}")
            print(f"❌ Errors: {result.errors}")
            print(f"⏭️  Skipped: {result.skipped}")
            print(f"⏱️  Duration: {result.duration_seconds:.2f}s")
            
            # Швидкість
            if result.duration_seconds > 0:
                rate = result.total / result.duration_seconds
                print(f"⚡ Speed: {rate:.1f} products/second")
            
            # Success rate
            if result.total > 0:
                success_rate = (result.updated / result.total) * 100
                print(f"✅ Success rate: {success_rate:.1f}%")
            
            print("="*70)
            
            # Adapter stats
            adapter_stats = adapter.get_stats()
            print(f"📦 Adapter stats: {adapter_stats}")
            print("="*70)
            
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
        finally:
            await session.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Hourly Market Data Sync"
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
        help='Path to JSON/JSONL file with market data'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of products to sync'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Batch size for processing (larger for fast sync)'
    )
    
    args = parser.parse_args()
    
    # Запуск
    asyncio.run(run_hourly_sync(
        source=args.source,
        file_path=args.file,
        limit=args.limit,
        batch_size=args.batch_size
    ))


if __name__ == "__main__":
    main()
