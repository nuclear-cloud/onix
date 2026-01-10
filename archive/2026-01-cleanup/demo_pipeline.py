#!/usr/bin/env python3
"""
DEMO: Тест повного pipeline з тестовими даними.

Демонструє:
1. Повний імпорт (FULL MODE)
2. Швидкий маркет-синхронізацію (MARKET MODE)
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_db
from app.services.product_service import ProductService
from app.adapters.yakaboo import YakabooAdapter


# Тестові дані
TEST_PRODUCTS_FULL = [
    {
        "entity_id": 1001,
        "sku": "DUNE-001",
        "name": "Дюна",
        "status": 1,
        "price_info": {"final_price": 600.0, "regular_price": 750.0},
        "media_gallery_entries": [{"file": "dune_cover.jpg"}],
        "categories": [
            {"id": 1, "name": "Книги"},
            {"id": 2, "name": "Фантастика"}
        ],
        "custom_attributes": [
            {"attribute_code": "isbn13", "value": "978-0441172719"},
            {"attribute_code": "publisher_name", "value": "КСД"},
            {"attribute_code": "author", "value": "Френк Герберт"},
            {"attribute_code": "page_count", "value": "896"},
            {"attribute_code": "description", "value": "Епічна історія про пустельну планету..."},
            {"attribute_code": "stock_status", "value": "in_stock"},
        ]
    },
    {
        "entity_id": 1002,
        "sku": "KOBZAR-001",
        "name": "Кобзар",
        "status": 1,
        "price_info": {"final_price": 250.0, "regular_price": 300.0},
        "media_gallery_entries": [{"file": "kobzar.jpg"}],
        "categories": [
            {"id": 1, "name": "Книги"},
            {"id": 2, "name": "Поезія"}
        ],
        "custom_attributes": [
            {"attribute_code": "isbn13", "value": "978-9660123456"},
            {"attribute_code": "publisher_name", "value": "А-БА-БА-ГА-ЛА-МА-ГА"},
            {"attribute_code": "author", "value": "Тарас Шевченко"},
            {"attribute_code": "page_count", "value": "512"},
            {"attribute_code": "description", "value": "Збірка віршів великого Кобзаря"},
            {"attribute_code": "stock_status", "value": "in_stock"},
        ]
    }
]

# Оновлені ціни (для market sync)
TEST_PRODUCTS_MARKET = [
    {
        "entity_id": 1001,
        "sku": "DUNE-001",
        "price_info": {"final_price": 550.0, "regular_price": 750.0},  # Знижка!
        "custom_attributes": [
            {"attribute_code": "isbn13", "value": "978-0441172719"},
            {"attribute_code": "stock_status", "value": "in_stock"},
        ]
    },
    {
        "entity_id": 1002,
        "sku": "KOBZAR-001",
        "price_info": {"final_price": 300.0, "regular_price": 300.0},  # Ціна виросла
        "custom_attributes": [
            {"attribute_code": "isbn13", "value": "978-9660123456"},
            {"attribute_code": "stock_status", "value": "out_of_stock"},  # Розпродали!
        ]
    }
]


async def demo_full_import():
    """Демо: Повний імпорт."""
    print("\n" + "="*70)
    print("🌅 DEMO: FULL IMPORT MODE")
    print("="*70 + "\n")
    
    async for session in get_db():
        service = ProductService(session)
        adapter = YakabooAdapter()
        
        try:
            stats = await service.import_full_batch(
                raw_products=TEST_PRODUCTS_FULL,
                adapter=adapter,
                batch_size=10
            )
            
            print(f"\n✅ Full import completed: {stats}")
            
            # Перевіряємо що створилось
            count = await service.count_products(source="yakaboo")
            print(f"📊 Total Yakaboo products in DB: {count}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await session.close()


async def demo_market_sync():
    """Демо: Швидке оновлення цін."""
    print("\n" + "="*70)
    print("⚡ DEMO: MARKET SYNC MODE")
    print("="*70 + "\n")
    
    # Чекаємо трохи щоб було видно різницю
    await asyncio.sleep(1)
    
    async for session in get_db():
        service = ProductService(session)
        adapter = YakabooAdapter()
        
        try:
            result = await service.update_market_batch(
                raw_products=TEST_PRODUCTS_MARKET,
                adapter=adapter,
                batch_size=10
            )
            
            print(f"\n⚡ Market sync completed:")
            print(f"   Updated: {result.updated}")
            print(f"   Duration: {result.duration_seconds:.2f}s")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await session.close()


async def main():
    """Запуск повного демо."""
    print("="*70)
    print("🎬 YAKABOO PIPELINE DEMO")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Крок 1: Повний імпорт
    await demo_full_import()
    
    # Крок 2: Швидкий market sync
    await demo_market_sync()
    
    print("\n" + "="*70)
    print("🎉 DEMO COMPLETED!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
