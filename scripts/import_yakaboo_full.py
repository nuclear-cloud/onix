#!/usr/bin/env python3
"""
YAKABOO DATA IMPORT SCRIPT (Prisma)
====================================

Simple, clean Prisma-based import.

Usage:
    # Test with 100 records
    python scripts/import_yakaboo_full.py data/yakaboo_complete_final.jsonl --limit 100

    # Dry run (validation only)
    python scripts/import_yakaboo_full.py data/yakaboo_complete_final.jsonl --limit 1000 --dry-run

    # Full import
    python scripts/import_yakaboo_full.py data/yakaboo_complete_final.jsonl
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.data_adapter import YakabooDataAdapter
from app.services.prisma_ingestion_service import (
    PrismaIngestionService,
    ImportMetrics,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='Import Yakaboo data to PostgreSQL via Prisma')
    
    parser.add_argument('file_path', help='Path to JSONL file')
    parser.add_argument('--limit', '-l', type=int, default=None, help='Max records to import')
    parser.add_argument('--dry-run', action='store_true', help='Validate only, no DB writes')
    parser.add_argument('--log-every', '-e', type=int, default=1000, help='Log every N records')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--output-errors', '-o', type=str, help='Write errors to JSON file')
    
    return parser.parse_args()


class ProgressBar:
    """Simple progress bar."""
    
    def __init__(self, total: int, width: int = 50):
        self.total = total
        self.width = width
        self.start_time = datetime.now()
    
    def update(self, current: int, total: int = None):
        if total:
            self.total = total
        if self.total == 0:
            return
        
        progress = current / self.total
        filled = int(self.width * progress)
        bar = '█' * filled + '░' * (self.width - filled)
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if current > 0 and elapsed > 0:
            rate = current / elapsed
            remaining = (self.total - current) / rate if rate > 0 else 0
            eta = f"{remaining / 60:.1f}m" if remaining > 60 else f"{remaining:.0f}s"
        else:
            eta = "..."
        
        sys.stdout.write(f'\r|{bar}| {current:,}/{self.total:,} ({progress*100:.1f}%) ETA: {eta}    ')
        sys.stdout.flush()
    
    def finish(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        sys.stdout.write(f'\n✓ Completed in {elapsed:.1f}s\n')
        sys.stdout.flush()


async def run_dry_import(file_path: str, adapter: YakabooDataAdapter, limit: int = None) -> ImportMetrics:
    """Validation-only import (no DB writes)."""
    metrics = ImportMetrics()
    path = Path(file_path)
    
    logger.info(f"Counting records in {file_path}...")
    with open(path, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for _ in f)
    
    metrics.total_records = min(total_lines, limit) if limit else total_lines
    logger.info(f"Processing {metrics.total_records:,} records (dry-run mode)")
    
    progress = ProgressBar(metrics.total_records)
    
    with open(path, 'r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, 1):
            if limit and line_number > limit:
                break
            
            try:
                raw_data = json.loads(line.strip())
                result = adapter.transform(raw_data)
                
                if result.is_valid:
                    metrics.succeeded += 1
                else:
                    metrics.failed += 1
                    for error in result.errors:
                        metrics.add_error(
                            adapter.extract_identifier(raw_data),
                            error.message,
                            {'field': error.field, 'line': line_number}
                        )
                
                metrics.processed += 1
                
                if metrics.processed % 100 == 0:
                    progress.update(metrics.processed)
                    
            except json.JSONDecodeError as e:
                metrics.failed += 1
                metrics.add_error(f"line_{line_number}", f"Invalid JSON: {e}")
                metrics.processed += 1
            except Exception as e:
                metrics.failed += 1
                metrics.add_error(f"line_{line_number}", str(e))
                metrics.processed += 1
    
    progress.finish()
    metrics.finalize()
    return metrics


async def run_full_import(file_path: str, adapter: YakabooDataAdapter, limit: int = None, log_every: int = 1000) -> ImportMetrics:
    """Full import with Prisma DB writes."""
    service = PrismaIngestionService(adapter, log_every=log_every)
    
    progress = ProgressBar(0)
    
    def progress_callback(current: int, total: int):
        progress.update(current, total)
    
    metrics = await service.import_from_file(file_path, progress_callback, limit=limit)
    progress.finish()
    
    return metrics


async def main():
    args = parse_args()
    
    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    adapter = YakabooDataAdapter()
    
    # Banner
    print("\n" + "=" * 60)
    print("YAKABOO DATA IMPORT (Prisma)")
    print("=" * 60)
    print(f"  File:   {file_path}")
    print(f"  Limit:  {args.limit or 'None'}")
    print(f"  Mode:   {'DRY RUN' if args.dry_run else 'FULL IMPORT'}")
    print("=" * 60 + "\n")
    
    # Run import
    if args.dry_run:
        metrics = await run_dry_import(str(file_path), adapter, limit=args.limit)
    else:
        metrics = await run_full_import(str(file_path), adapter, limit=args.limit, log_every=args.log_every)
    
    # Summary
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    
    summary = metrics.to_dict()
    print(f"  Duration:     {summary['duration_seconds']:.1f} seconds")
    print(f"  Throughput:   {summary['records_per_second']:.1f} records/second")
    print()
    print(f"  Total:        {summary['total_records']:,}")
    print(f"  Processed:    {summary['processed']:,}")
    print(f"  Succeeded:    {summary['succeeded']:,}")
    print(f"  Failed:       {summary['failed']:,}")
    print(f"  Skipped:      {summary.get('skipped', 0):,}")
    print(f"  Success rate: {summary['success_rate']:.1f}%")
    print()
    print("  Nested entities:")
    for entity, count in summary['nested_entities'].items():
        if count > 0:
            print(f"    {entity}: {count:,}")
    print()
    print(f"  Errors:   {summary['error_count']}")
    print(f"  Warnings: {summary['warning_count']}")
    print("=" * 60 + "\n")
    
    # Output errors
    if args.output_errors and metrics.errors:
        with open(args.output_errors, 'w', encoding='utf-8') as f:
            json.dump({'errors': metrics.errors, 'summary': summary}, f, indent=2, ensure_ascii=False)
        print(f"Errors written to: {args.output_errors}")


if __name__ == "__main__":
    asyncio.run(main())
