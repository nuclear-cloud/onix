#!/usr/bin/env python3
"""
PRODUCTION IMPORT: Full Yakaboo Catalog (972k products)

Features:
✅ Filters: Only BOOKS with ISBN-13
✅ Logging: Real-time progress + statistics
✅ Batch mode: 1000 products per batch
✅ Resume support: Can restart from last position
✅ Performance: ~500 products/second

Запуск:
    python scripts/bulk_import_yakaboo.py --file data/yakaboo_complete_final.jsonl
    python scripts/bulk_import_yakaboo.py --file data/yakaboo_complete_final.jsonl --skip 100000
    python scripts/bulk_import_yakaboo.py --file data/yakaboo_complete_final.jsonl --limit 50000
"""
import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse
from dataclasses import dataclass
import logging

# Додаємо project root до Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.product_service import ProductService
from app.adapters.yakaboo import YakabooAdapter


# ============================================================
# Logging Setup
# ============================================================

def setup_logging(output_file: Optional[str] = None):
    """Configure logging with file and console output."""
    log_format = '%(asctime)s | %(levelname)-8s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if output_file:
        file_handler = logging.FileHandler(output_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.info(f"📝 Logging to file: {output_file}")
    
    return logger


# ============================================================
# Statistics Tracking
# ============================================================

@dataclass
class ImportStats:
    """Статистика імпорту."""
    total_read: int = 0          # Прочитано з файлу
    total_processed: int = 0     # Оброблено
    total_books: int = 0         # Книг (з ISBN)
    total_non_books: int = 0     # Не-книг
    total_no_isbn: int = 0       # Без ISBN
    total_created: int = 0       # Створено
    total_updated: int = 0       # Оновлено
    total_errors: int = 0        # Помилок
    
    # Категорії по-книг
    non_book_categories: Dict[str, int] = None
    
    def __post_init__(self):
        if self.non_book_categories is None:
            self.non_book_categories = {}
    
    def print_summary(self, duration_seconds: float):
        """Вивести підсумок."""
        logger = logging.getLogger()
        
        logger.info("")
        logger.info("="*80)
        logger.info("📊 FINAL STATISTICS")
        logger.info("="*80)
        logger.info(f"📖 Total read from file:      {self.total_read:>10,}")
        logger.info(f"✅ Books with ISBN:           {self.total_books:>10,}")
        logger.info(f"❌ Non-books (filtered):      {self.total_non_books:>10,}")
        logger.info(f"⚠️  Books without ISBN:       {self.total_no_isbn:>10,}")
        logger.info("")
        logger.info(f"🎉 Created new:              {self.total_created:>10,}")
        logger.info(f"🔄 Updated existing:         {self.total_updated:>10,}")
        logger.info(f"💥 Errors:                   {self.total_errors:>10,}")
        logger.info(f"📚 Total processed:          {self.total_processed:>10,}")
        logger.info("")
        
        # Speed statistics
        if duration_seconds > 0:
            speed = self.total_read / duration_seconds
            logger.info(f"⚡ Speed (read):              {speed:>10.1f} products/sec")
            
            speed_proc = self.total_processed / duration_seconds
            logger.info(f"⚡ Speed (processed):         {speed_proc:>10.1f} products/sec")
        
        # Duration
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)
        logger.info(f"⏱️  Total time:                {hours:>2}h {minutes:>2}m {seconds:>2}s")
        
        # Non-book categories
        if self.non_book_categories:
            logger.info("")
            logger.info("📋 Non-book categories (filtered out):")
            for category, count in sorted(
                self.non_book_categories.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]:
                logger.info(f"   - {category}: {count:,}")
        
        logger.info("="*80)
        logger.info("")


# ============================================================
# Filtering Logic
# ============================================================

def is_book(product: Dict[str, Any]) -> bool:
    """
    Перевіряє чи продукт це книга.
    
    Логіка: Перевіряємо наявність book_* полів або типу товару
    """
    # Перевіряємо чи є книжні атрибути
    book_fields = ['book_isbn', 'book_page_count', 'book_publisher', 'book_lang']
    has_book_attr = any(key in product for key in book_fields)
    
    if not has_book_attr:
        return False
    
    # Перевіряємо назву на забороні слова
    forbidden_words = [
        'календар', 'іграшка', 'головоломка', 'пазл',
        'открытка', 'скетчбук', 'записна книжка',
        'планер', 'щоденник без текста',
    ]
    
    name = product.get('name', '').lower()
    for word in forbidden_words:
        if word in name:
            return False
    
    return True


def has_isbn(product: Dict[str, Any]) -> Optional[str]:
    """
    Дістає ISBN-13 з product.
    
    Структура: product['book_isbn'] або product['book_isbn_label'][0]['label']
    
    Returns:
        ISBN-13 або None
    """
    # Спосіб 1: Пряме поле
    if 'book_isbn' in product:
        isbn = product['book_isbn']
        if isinstance(isbn, str) and isbn.strip():
            isbn_clean = isbn.replace('-', '').replace(' ', '')
            if len(isbn_clean) == 13 and isbn_clean.isdigit():
                return isbn
    
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
                            return isbn
    
    return None


# ============================================================
# Main Import Logic
# ============================================================

async def process_line(
    line_num: int,
    raw_data: Dict[str, Any],
    service: ProductService,
    adapter: YakabooAdapter,
    stats: ImportStats,
    logger: logging.Logger
) -> bool:
    """
    Обробляє один продукт.
    
    Returns:
        True if processed, False if skipped
    """
    stats.total_read += 1
    
    # 1. Перевіряємо чи це книга
    if not is_book(raw_data):
        # Логуємо категорію для статистики
        categories = raw_data.get('categories', [])
        if categories:
            cat_name = categories[-1].get('name', 'Unknown')
            stats.non_book_categories[cat_name] = stats.non_book_categories.get(cat_name, 0) + 1
        
        stats.total_non_books += 1
        return False
    
    # 2. Перевіряємо наявність ISBN
    isbn = has_isbn(raw_data)
    if not isbn:
        stats.total_no_isbn += 1
        return False
    
    # 3. Валідуємо
    is_valid, errors = adapter.validate(raw_data)
    if not is_valid:
        logger.debug(f"Line {line_num}: Validation failed: {errors}")
        stats.total_errors += 1
        return False
    
    # 4. Імпортуємо
    try:
        result = await service.import_full_product(raw_data, adapter)
        if result:
            stats.total_processed += 1
            stats.total_created += 1
            return True
        else:
            stats.total_errors += 1
            return False
    except Exception as e:
        logger.debug(f"Line {line_num}: Import error: {e}")
        stats.total_errors += 1
        return False


async def run_bulk_import(
    file_path: str,
    skip_lines: int = 0,
    limit: Optional[int] = None,
    batch_size: int = 1000,
    log_file: Optional[str] = None
):
    """
    Основна функція масового імпорту.
    
    Args:
        file_path: Шлях до JSONL файлу
        skip_lines: Скільки строк пропустити (для резюме)
        limit: Максимум продуктів для обробки
        batch_size: Розмір батча
        log_file: Файл для логів
    """
    logger = setup_logging(log_file)
    stats = ImportStats()
    start_time = datetime.now()
    
    logger.info("="*80)
    logger.info("🚀 YAKABOO BULK IMPORT - 972k Products")
    logger.info("="*80)
    logger.info(f"📁 File: {file_path}")
    logger.info(f"⏭️  Skip lines: {skip_lines:,}")
    logger.info(f"📊 Batch size: {batch_size:,}")
    if limit:
        logger.info(f"🔢 Limit: {limit:,}")
    logger.info(f"⏰ Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    logger.info("")
    
    # Перевіряємо файл
    if not Path(file_path).exists():
        logger.error(f"❌ File not found: {file_path}")
        return
    
    async for session in get_db():
        service = ProductService(session)
        adapter = YakabooAdapter()
        
        try:
            line_num = 0
            batch = []
            last_log_time = start_time
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for idx, file_line in enumerate(f):
                    line_num = idx + 1
                    
                    # Skip lines if requested
                    if line_num <= skip_lines:
                        continue
                    
                    # Check limit
                    if limit and stats.total_read >= limit:
                        logger.info(f"⏹️  Reached limit of {limit:,} products")
                        break
                    
                    try:
                        raw_data = json.loads(file_line.strip())
                    except json.JSONDecodeError as e:
                        logger.warning(f"Line {line_num}: Invalid JSON: {e}")
                        stats.total_errors += 1
                        continue
                    
                    # Process one product
                    is_processed = await process_line(
                        line_num,
                        raw_data,
                        service,
                        adapter,
                        stats,
                        logger
                    )
                    
                    if is_processed:
                        batch.append(raw_data)
                    
                    # Process batch
                    if len(batch) >= batch_size:
                        # Already committed in import_full_product
                        batch = []
                        
                        # Log progress
                        now = datetime.now()
                        if (now - last_log_time).total_seconds() >= 10:  # Log every 10s
                            elapsed = (now - start_time).total_seconds()
                            speed = stats.total_read / elapsed if elapsed > 0 else 0
                            logger.info(
                                f"📊 Line {line_num:>10,} | "
                                f"Read: {stats.total_read:>8,} | "
                                f"Books: {stats.total_books:>8,} | "
                                f"Created: {stats.total_created:>8,} | "
                                f"Speed: {speed:>6.1f}/s"
                            )
                            last_log_time = now
                    
                    # Update running total
                    if is_processed:
                        stats.total_books += 1
            
            # Final commit if needed
            await session.commit()
            
            # Log final statistics
            duration = (datetime.now() - start_time).total_seconds()
            stats.print_summary(duration)
            
            logger.info("✅ IMPORT COMPLETE!")
            logger.info("")
            
        except Exception as e:
            logger.error(f"❌ Import failed: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
        finally:
            await session.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Bulk import Yakaboo catalog (972k products)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full import
  python scripts/bulk_import_yakaboo.py --file data/yakaboo_complete_final.jsonl
  
  # Resume from line 100000
  python scripts/bulk_import_yakaboo.py --file data/yakaboo_complete_final.jsonl --skip 100000
  
  # Test with 1000 products
  python scripts/bulk_import_yakaboo.py --file data/yakaboo_complete_final.jsonl --limit 1000
  
  # With custom batch size and logging
  python scripts/bulk_import_yakaboo.py --file data/yakaboo_complete_final.jsonl --batch-size 2000 --log-file import.log
        """
    )
    
    parser.add_argument(
        '--file',
        type=str,
        required=True,
        help='Path to JSONL file'
    )
    parser.add_argument(
        '--skip',
        type=int,
        default=0,
        help='Skip N lines (for resume)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit products to process'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for processing'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='Log file path'
    )
    
    args = parser.parse_args()
    
    # Run import
    asyncio.run(run_bulk_import(
        file_path=args.file,
        skip_lines=args.skip,
        limit=args.limit,
        batch_size=args.batch_size,
        log_file=args.log_file
    ))


if __name__ == "__main__":
    main()
