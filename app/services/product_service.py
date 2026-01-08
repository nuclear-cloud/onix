# app/services/product_service.py
"""
Сервіс управління продуктами: "Завскладом" + "Мерчендайзер".

Два режими роботи:
1. FULL MODE (Шлях 1) - Щоденний імпорт каталогу
2. MARKET MODE (Шлях 2) - Погодинне оновлення цін
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
import asyncio

from app.models.catalog import CatalogProduct, Publisher
from app.schemas.product_full import ProductFullDTO, ProductCreateDTO
from app.schemas.product_market import ProductMarketDTO, MarketUpdateResult
from app.adapters import YakabooAdapter


class ProductService:
    """
    Головний сервіс для роботи з продуктами.
    
    Responsibilities:
    - Створення нових продуктів
    - Оновлення існуючих (повне і часткове)
    - Синхронізація з джерелами даних
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.yakaboo = YakabooAdapter()
    
    # ============================================================
    # ШЛЯХ 1: ПОВНИЙ ІМПОРТ КАТАЛОГУ (Daily Catalog)
    # ============================================================
    
    async def import_full_product(
        self,
        raw_data: Dict[str, Any],
        adapter: YakabooAdapter
    ) -> Optional[CatalogProduct]:
        """
        Повний імпорт одного продукту.
        
        Args:
            raw_data: Сирі дані від джерела
            adapter: Адаптер для парсингу
            
        Returns:
            CatalogProduct або None якщо помилка
        """
        try:
            # 1. Валідація
            is_valid, errors = adapter.validate(raw_data)
            if not is_valid:
                adapter.log_error(f"Validation failed: {errors}")
                return None
            
            # 2. Парсинг (повний режим)
            parsed = adapter.parse_full(raw_data)
            dto = ProductFullDTO(**parsed)
            
            # 3. Пошук існуючого
            existing = await self.get_by_isbn13(dto.isbn13)
            
            if existing:
                # Оновлюємо існуючий
                updated = await self._update_full_product(existing, dto)
                adapter.log_success(f"Updated: {dto.name} ({dto.isbn13})")
                return updated
            else:
                # Створюємо новий
                created = await self._create_full_product(dto)
                adapter.log_success(f"Created: {dto.name} ({dto.isbn13})")
                return created
                
        except Exception as e:
            adapter.log_error(f"Import failed: {str(e)}")
            return None
    
    async def import_full_batch(
        self,
        raw_products: List[Dict[str, Any]],
        adapter: YakabooAdapter,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Повний імпорт списку продуктів (пакетний режим).
        
        Args:
            raw_products: Список сирих даних
            adapter: Адаптер
            batch_size: Розмір пакету
            
        Returns:
            Статистика: {created, updated, errors, skipped}
        """
        stats = {"created": 0, "updated": 0, "errors": 0, "skipped": 0}
        total = len(raw_products)
        
        print(f"🚀 Starting FULL import: {total} products")
        
        for i in range(0, total, batch_size):
            batch = raw_products[i:i + batch_size]
            print(f"📦 Processing batch {i//batch_size + 1}/{(total-1)//batch_size + 1}")
            
            for raw_data in batch:
                result = await self.import_full_product(raw_data, adapter)
                
                if result:
                    if result.id:  # Existing (updated)
                        stats["updated"] += 1
                    else:
                        stats["created"] += 1
                else:
                    stats["errors"] += 1
            
            # Commit після кожного батча
            await self.db.commit()
        
        print(f"✅ FULL import completed: {stats}")
        return stats
    
    # ============================================================
    # ШЛЯХ 2: ШВИДКЕ ОНОВЛЕННЯ ЦІН (Hourly Market Sync)
    # ============================================================
    
    async def update_market_data(
        self,
        raw_data: Dict[str, Any],
        adapter: YakabooAdapter
    ) -> Optional[CatalogProduct]:
        """
        Швидке оновлення тільки маркет-даних (ціна, наявність).
        
        Args:
            raw_data: Сирі дані від джерела
            adapter: Адаптер
            
        Returns:
            CatalogProduct або None
        """
        try:
            # 1. Швидкий парсинг (тільки критичні поля)
            parsed = adapter.parse_market(raw_data)
            dto = ProductMarketDTO(**parsed)
            
            # 2. Пошук продукту
            product = await self.get_by_isbn13(dto.isbn13)
            
            if not product:
                # Продукт не знайдено - пропускаємо
                # (в режимі market ми НЕ створюємо нові продукти)
                adapter.log_warning(f"Product not found: {dto.isbn13}")
                return None
            
            # 3. Оновлення тільки маркет-полів
            updated = await self._update_market_fields(product, dto)
            adapter.log_success(f"Market updated: {dto.isbn13}")
            
            return updated
            
        except Exception as e:
            adapter.log_error(f"Market update failed: {str(e)}")
            return None
    
    async def update_market_batch(
        self,
        raw_products: List[Dict[str, Any]],
        adapter: YakabooAdapter,
        batch_size: int = 500  # Більший батч для швидкої операції
    ) -> MarketUpdateResult:
        """
        Пакетне оновлення маркет-даних.
        
        Args:
            raw_products: Список сирих даних
            adapter: Адаптер
            batch_size: Розмір пакету
            
        Returns:
            MarketUpdateResult з статистикою
        """
        start_time = datetime.now()
        stats = {
            "total": len(raw_products),
            "updated": 0,
            "created": 0,
            "errors": 0,
            "skipped": 0
        }
        
        print(f"⚡ Starting MARKET sync: {stats['total']} products")
        
        for i in range(0, stats['total'], batch_size):
            batch = raw_products[i:i + batch_size]
            print(f"📦 Processing batch {i//batch_size + 1}/{(stats['total']-1)//batch_size + 1}")
            
            for raw_data in batch:
                result = await self.update_market_data(raw_data, adapter)
                
                if result:
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            
            # Commit після батча
            await self.db.commit()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = MarketUpdateResult(
            total=stats["total"],
            updated=stats["updated"],
            created=stats["created"],
            errors=stats["errors"],
            skipped=stats["skipped"],
            duration_seconds=duration
        )
        
        print(f"⚡ MARKET sync completed in {duration:.1f}s: {result.dict()}")
        return result
    
    # ============================================================
    # ПРИВАТНІ МЕТОДИ (Internal Operations)
    # ============================================================
    
    async def _create_full_product(self, dto: ProductFullDTO) -> CatalogProduct:
        """Створює новий продукт з повними даними."""
        product = CatalogProduct(
            record_reference=dto.isbn13,  # Using ISBN as record reference
            isbn_13=dto.isbn13,
            sku=dto.sku,
            product_form="BB",  # Default: Hardback book (ONIX List 150 code)
            # Store full data in JSONB for now
            onix_full={
                "title": dto.name,
                "author": dto.author,
                "publisher": dto.publisher,
                "description": dto.description,
                "short_description": dto.short_description,
                "pages": dto.pages,
                "year": dto.year,
                "language": dto.language,
                "binding": dto.binding,
                "thema_subject": dto.thema_subject,
                "categories": dto.categories,
                # Market data
                "price": dto.price,
                "old_price": dto.old_price,
                "currency": dto.currency,
                "in_stock": dto.in_stock,
                "url": dto.url,
                "source": dto.source,
                "external_id": dto.external_id,
                "main_image": dto.main_image,
                "images": dto.images,
            }
        )
        
        self.db.add(product)
        await self.db.flush()
        return product
    
    async def _update_full_product(
        self,
        product: CatalogProduct,
        dto: ProductFullDTO
    ) -> CatalogProduct:
        """Оновлює всі поля існуючого продукту."""
        # Update JSONB field
        if product.onix_full is None:
            product.onix_full = {}
        
        product.onix_full.update({
            "title": dto.name,
            "author": dto.author,
            "publisher": dto.publisher,
            "description": dto.description,
            "short_description": dto.short_description,
            "pages": dto.pages,
            "year": dto.year,
            "language": dto.language,
            "binding": dto.binding,
            "thema_subject": dto.thema_subject,
            "categories": dto.categories,
            # Market data
            "price": dto.price,
            "old_price": dto.old_price,
            "currency": dto.currency,
            "in_stock": dto.in_stock,
            "url": dto.url,
            "main_image": dto.main_image,
            "images": dto.images,
        })
        
        # Flag JSONB as modified
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(product, "onix_full")
        
        product.updated_at = datetime.utcnow()
        
        await self.db.flush()
        return product
    
    async def _update_market_fields(
        self,
        product: CatalogProduct,
        dto: ProductMarketDTO
    ) -> CatalogProduct:
        """
        Оновлює ТІЛЬКИ маркет-поля (швидка операція).
        НЕ чіпає опис, автора, видавництво, etc.
        """
        if product.onix_full is None:
            product.onix_full = {}
        
        product.onix_full.update({
            "price": dto.price,
            "old_price": dto.old_price,
            "currency": dto.currency,
            "in_stock": dto.in_stock,
            "url": dto.url,
        })
        
        # Flag JSONB as modified
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(product, "onix_full")
        
        product.updated_at = datetime.utcnow()
        
        await self.db.flush()
        return product
    
    # ============================================================
    # ДОПОМІЖНІ МЕТОДИ (Helpers)
    # ============================================================
    
    async def get_by_isbn13(self, isbn13: str) -> Optional[CatalogProduct]:
        """Знайти продукт по ISBN-13."""
        result = await self.db.execute(
            select(CatalogProduct).where(CatalogProduct.isbn_13 == isbn13)
        )
        return result.scalars().first()
    
    async def get_by_source_id(
        self,
        source: str,
        external_id: str
    ) -> Optional[CatalogProduct]:
        """Знайти продукт по ID джерела."""
        result = await self.db.execute(
            select(CatalogProduct).where(
                CatalogProduct.sku == external_id
            )
        )
        return result.scalars().first()
    
    async def count_products(self, source: Optional[str] = None) -> int:
        """Порахувати кількість продуктів."""
        from sqlalchemy import func
        
        query = select(func.count(CatalogProduct.id))
        # Note: source filtering would require querying JSONB
        
        result = await self.db.execute(query)
        return result.scalar()
    
    async def get_products_without_description(
        self,
        limit: int = 100
    ) -> List[CatalogProduct]:
        """Знайти продукти без опису (для повного оновлення)."""
        # This would require JSONB queries in real implementation
        result = await self.db.execute(
            select(CatalogProduct).limit(limit)
        )
        return list(result.scalars().all())
