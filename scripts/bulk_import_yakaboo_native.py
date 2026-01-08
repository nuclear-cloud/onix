#!/usr/bin/env python3
"""
📚 Bulk import 972k продуктів з Yakaboo каталогу.

Features:
  ✅ Фільтрування: тільки книги (book_* атрибути)
  ✅ ISBN-13 обов'язково
  ✅ Детальне логування (console + file)
  ✅ Прогрес кожні 10 секунд
  ✅ Підсумок: імпортовано / відфільтровано / помилки
  ✅ Resume: можна пропустити N рядків якщо перервалось
  ✅ Статистика: які товари відфільтровані, чому

Usage:
  python scripts/bulk_import_yakaboo_native.py \
    --file data/yakaboo_complete_final.jsonl \
    --batch-size 2000 \
    --log-file /var/log/yakaboo_import.log

Resume (перестартувати з рядка 50000):
  python scripts/bulk_import_yakaboo_native.py \
    --file data/yakaboo_complete_final.jsonl \
    --skip-lines 50000 \
    --batch-size 2000
"""

import sys
import json
import argparse
import logging
import asyncio
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from collections import defaultdict
from datetime import datetime

# Додаємо проект до path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# SQLAlchemy + DB
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.catalog import CatalogProduct
from app.core.config import settings

# Адаптер та сервіс
from app.adapters.yakaboo_native import YakabooNativeAdapter


@dataclass
class ImportStats:
    """Статистика імпорту."""
    total_read: int = 0
    books_imported: int = 0
    books_updated: int = 0
    books_with_isbn: int = 0
    books_without_isbn: int = 0
    non_books: int = 0
    errors: int = 0
    db_errors: int = 0
    
    # Причини відфільтрування
    filtered_reasons: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Час
    start_time: Optional[float] = None
    last_progress_time: Optional[float] = None
    end_time: Optional[float] = None
    
    def duration_sec(self) -> float:
        """Тривалість в секундах."""
        if not self.start_time:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time
    
    def books_total(self) -> int:
        """Всього книг (успішні + помилки)."""
        return self.books_imported + self.books_updated + self.db_errors
    
    def speed_read(self) -> float:
        """Товарів/сек прочитано."""
        duration = self.duration_sec()
        return self.total_read / duration if duration > 0 else 0
    
    def speed_books(self) -> float:
        """Книг/сек збережено."""
        duration = self.duration_sec()
        book_count = self.books_imported + self.books_updated
        return book_count / duration if duration > 0 else 0
    
    def report(self) -> str:
        """Красиво відформатована статистика."""
        lines = [
            "\n" + "=" * 60,
            "📊 ЗВІТ ІМПОРТУ YAKABOO",
            "=" * 60,
            f"⏱️  Тривалість: {self.duration_sec():.1f} сек",
            f"📈 Прочитано товарів: {self.total_read:,}",
            f"⚡ Швидкість читання: {self.speed_read():.0f} товарів/сек",
            "",
            "✅ УСПІШНІ:",
            f"   📚 Книг імпортовано (нові): {self.books_imported:,}",
            f"   🔄 Книг оновлено: {self.books_updated:,}",
            f"   📖 Всього книг: {self.books_total():,}",
            f"   🔖 Книг з ISBN: {self.books_with_isbn:,}",
            f"   ❌ Книг без ISBN: {self.books_without_isbn:,}",
            f"   ⚡ Швидкість збереження: {self.speed_books():.0f} книг/сек",
            "",
            "❌ ПОМИЛКИ:",
            f"   🚨 Помилок парсингу: {self.errors:,}",
            f"   💾 Помилок БД: {self.db_errors:,}",
            "",
            "🚫 ВІДФІЛЬТРОВАНО:",
            f"   📦 Не-книги: {self.non_books:,}",
        ]
        
        if self.filtered_reasons:
            lines.append("   Причини відфільтрування:")
            for reason, count in sorted(
                self.filtered_reasons.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]:
                lines.append(f"     - {reason}: {count:,}")
        
        lines.extend([
            "",
            "=" * 60,
            f"✨ Завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
        ])
        
        return "\n".join(lines)


def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """Налаштування логування."""
    logger = logging.getLogger("yakaboo_import")
    logger.setLevel(logging.DEBUG)
    
    # Console handler - INFO
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)
    
    # File handler - DEBUG (якщо задано)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            '%(asctime)s [%(levelname)-8s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
        logger.info(f"📝 Логування до файлу: {log_file}")
    
    return logger


def is_book(product: Dict[str, Any]) -> bool:
    """Перевіряє, чи це книга (за атрибутами)."""
    # Повинні бути book_* атрибути
    book_fields = ['book_isbn', 'book_page_count', 'book_publisher', 'book_lang']
    has_book_attr = any(key in product for key in book_fields)
    
    if not has_book_attr:
        return False
    
    # Виключаємо товари за назвою
    forbidden_words = [
        'календар', 'календарь',  # Календарі
        'іграшка', 'игрушка',  # Іграшки
        'головоломка', 'головоломки',  # Головоломки
        'пазл', 'пазлы',  # Пазли
        'нарисник',  # Книжки для малювання
        'раскраска', 'розмальовка',  # Розмальовки
    ]
    
    name = product.get('name', '').lower()
    for word in forbidden_words:
        if word in name:
            return False
    
    return True


def has_isbn(product: Dict[str, Any]) -> Optional[str]:
    """Витягує та валідує ISBN-13."""
    # Спосіб 1: Пряме поле
    if 'book_isbn' in product:
        isbn = product['book_isbn']
        if isinstance(isbn, str) and isbn.strip():
            isbn_clean = isbn.replace('-', '').replace(' ', '')
            if len(isbn_clean) == 13 and isbn_clean.isdigit():
                return isbn_clean
    
    # Спосіб 2: Через label
    if 'book_isbn_label' in product:
        labels = product['book_isbn_label']
        if isinstance(labels, list) and labels:
            for label_obj in labels:
                if isinstance(label_obj, dict):
                    isbn = label_obj.get('label', '')
                    if isbn and isinstance(isbn, str):
                        isbn_clean = isbn.replace('-', '').replace(' ', '')
                        if len(isbn_clean) == 13 and isbn_clean.isdigit():
                            return isbn_clean
    
    return None


async def process_line(
    line: str,
    adapter: YakabooNativeAdapter,
    stats: ImportStats,
    logger: logging.Logger,
) -> Optional[Dict[str, Any]]:
    """Обробляє один рядок JSON."""
    try:
        product = json.loads(line)
        stats.total_read += 1
        
        # Перевіра: чи це книга?
        if not is_book(product):
            stats.non_books += 1
            name = product.get('name', 'Unknown')
            stats.filtered_reasons['Non-book product'] += 1
            logger.debug(f"⚠️  Не-книга: {name[:50]}")
            return None
        
        # Перевіра: чи є ISBN?
        isbn = has_isbn(product)
        if not isbn:
            stats.books_without_isbn += 1
            name = product.get('name', 'Unknown')
            stats.filtered_reasons['No ISBN-13'] += 1
            logger.debug(f"⚠️  Без ISBN: {name[:50]}")
            return None
        
        stats.books_with_isbn += 1
        
        # Парсинг через адаптер
        parsed = adapter.parse_full(product)
        parsed['isbn13'] = isbn
        
        return parsed
        
    except json.JSONDecodeError as e:
        stats.errors += 1
        logger.error(f"❌ JSON помилка: {str(e)[:100]}")
        return None
    except Exception as e:
        stats.errors += 1
        logger.error(f"❌ Помилка обробки: {str(e)[:100]}")
        return None


async def run_bulk_import(
    file_path: str,
    db_url: str,
    batch_size: int = 1000,
    skip_lines: int = 0,
    limit: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
) -> ImportStats:
    """Основна функція імпорту."""
    if logger is None:
        logger = setup_logging()
    
    logger.info(f"🚀 Запуск імпорту")
    logger.info(f"📁 Файл: {file_path}")
    logger.info(f"🔢 Розмір батчу: {batch_size}")
    if skip_lines > 0:
        logger.info(f"⏭️  Пропустити рядків: {skip_lines}")
    if limit:
        logger.info(f"📊 Максимум: {limit:,} товарів")
    
    # Ініціалізація
    stats = ImportStats()
    stats.start_time = time.time()
    stats.last_progress_time = stats.start_time
    
    adapter = YakabooNativeAdapter()
    
    # DB
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    batch: List[Dict[str, Any]] = []
    
    try:
        logger.info(f"📖 Читання {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                # Пропускаємо рядки
                if line_num < skip_lines:
                    continue
                
                # Ліміт
                if limit and stats.total_read >= limit:
                    logger.info(f"⛔ Досягнуто ліміту {limit:,}")
                    break
                
                # Обробка рядка
                parsed = await process_line(line, adapter, stats, logger)
                if parsed:
                    batch.append(parsed)
                
                # Батч заповнений - зберігаємо
                if len(batch) >= batch_size:
                    async with async_session() as session:
                        try:
                            for product_data in batch:
                                # Пошук чи оновлення
                                isbn13 = product_data.get('isbn13')
                                sku = product_data.get('sku', '')
                                
                                # Шукаємо існуючий продукт
                                result = await session.execute(
                                    select(CatalogProduct).where(
                                        CatalogProduct.isbn_13 == isbn13
                                    )
                                )
                                product = result.scalar_one_or_none()
                                
                                if product:
                                    # Оновлення
                                    product.sku = sku
                                    stats.books_updated += 1
                                else:
                                    # Створення
                                    new_product = CatalogProduct(
                                        isbn_13=isbn13,
                                        sku=sku,
                                        product_form="BB",  # Book
                                        record_reference=f"yakaboo-{isbn13}",
                                    )
                                    session.add(new_product)
                                    stats.books_imported += 1
                            
                            await session.commit()
                            logger.debug(f"✅ Батч {len(batch)} товарів збережено")
                            
                        except Exception as e:
                            await session.rollback()
                            stats.db_errors += len(batch)
                            logger.error(f"💾 Помилка БД: {str(e)[:100]}")
                    
                    batch = []
                
                # Прогрес
                now = time.time()
                if now - stats.last_progress_time >= 10:
                    progress_str = (
                        f"📊 {stats.total_read:,} прочитано, "
                        f"{stats.books_with_isbn:,} книг (OK), "
                        f"{stats.non_books:,} не-книг, "
                        f"{stats.books_imported + stats.books_updated:,} в БД"
                    )
                    logger.info(progress_str)
                    stats.last_progress_time = now
        
        # Останній батч
        if batch:
            async with async_session() as session:
                try:
                    for product_data in batch:
                        isbn13 = product_data.get('isbn13')
                        sku = product_data.get('sku', '')
                        
                        # Шукаємо існуючий продукт
                        result = await session.execute(
                            select(CatalogProduct).where(
                                CatalogProduct.isbn_13 == isbn13
                            )
                        )
                        product = result.scalar_one_or_none()
                        
                        if product:
                            product.sku = sku
                            stats.books_updated += 1
                        else:
                            new_product = CatalogProduct(
                                isbn_13=isbn13,
                                sku=sku,
                                product_form="BB",
                                record_reference=f"yakaboo-{isbn13}",
                            )
                            session.add(new_product)
                            stats.books_imported += 1
                    
                    await session.commit()
                    logger.debug(f"✅ Останній батч {len(batch)} товарів")
                    
                except Exception as e:
                    await session.rollback()
                    stats.db_errors += len(batch)
                    logger.error(f"💾 Помилка БД останнього батча: {str(e)[:100]}")
        
        stats.end_time = time.time()
        logger.info(stats.report())
        
        return stats
        
    except FileNotFoundError:
        logger.error(f"❌ Файл не знайден: {file_path}")
        raise
    except KeyboardInterrupt:
        logger.warning(f"⚠️  Перервано користувачем")
        stats.end_time = time.time()
        logger.warning(f"📊 Проміжна статистика:\n{stats.report()}")
        raise
    except Exception as e:
        logger.error(f"❌ Критична помилка: {str(e)}")
        stats.end_time = time.time()
        logger.error(stats.report())
        raise
    finally:
        await engine.dispose()


async def main():
    """CLI точка входу."""
    parser = argparse.ArgumentParser(
        description="Bulk import Yakaboo products",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        '--file', '-f',
        required=True,
        help='Path to JSONL file'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=1000,
        help='Batch size (default: 1000)'
    )
    parser.add_argument(
        '--skip-lines', '-s',
        type=int,
        default=0,
        help='Skip N lines (for resume)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Maximum products to import'
    )
    parser.add_argument(
        '--log-file',
        default=None,
        help='Log file path'
    )
    
    args = parser.parse_args()
    
    logger = setup_logging(args.log_file)
    
    try:
        db_url = settings.DATABASE_URL
        
        await run_bulk_import(
            file_path=args.file,
            db_url=db_url,
            batch_size=args.batch_size,
            skip_lines=args.skip_lines,
            limit=args.limit,
            logger=logger,
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
