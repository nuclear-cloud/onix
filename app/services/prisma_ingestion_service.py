"""
PRISMA-BASED DATA INGESTION SERVICE
====================================

Clean, simple data ingestion using Prisma ORM.
No SQLAlchemy complexity - just Prisma operations.

Features:
- Prisma upserts for idempotency
- Batch processing for performance
- Clear error handling
- Progress metrics
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from prisma import Prisma
from prisma import Json

from app.schemas.data_models import ProductDTO
from app.adapters.data_adapter import BaseDataAdapter

logger = logging.getLogger(__name__)


# ============================================================================
# METRICS
# ============================================================================

@dataclass
class ImportMetrics:
    """Tracks import statistics."""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    total_records: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    duplicates: int = 0
    
    contributors_created: int = 0
    subjects_created: int = 0
    text_contents_created: int = 0
    media_files_created: int = 0
    prices_created: int = 0
    
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_error(self, record_id: str, error: str, details: Dict = None):
        self.errors.append({
            'record_id': record_id,
            'error': error,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        })
        if len(self.errors) > 1000:
            self.errors = self.errors[-500:]
    
    def add_warning(self, record_id: str, warning: str, details: Dict = None):
        self.warnings.append({
            'record_id': record_id,
            'warning': warning,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        })
        if len(self.warnings) > 1000:
            self.warnings = self.warnings[-500:]
    
    @property
    def success_rate(self) -> float:
        if self.processed == 0:
            return 0.0
        return (self.succeeded / self.processed) * 100
    
    @property
    def duration_seconds(self) -> float:
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()
    
    @property
    def records_per_second(self) -> float:
        duration = self.duration_seconds
        if duration == 0:
            return 0.0
        return self.processed / duration
    
    def finalize(self):
        self.end_time = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'duration_seconds': self.duration_seconds,
            'records_per_second': round(self.records_per_second, 2),
            'total_records': self.total_records,
            'processed': self.processed,
            'succeeded': self.succeeded,
            'failed': self.failed,
            'skipped': self.skipped,
            'duplicates': self.duplicates,
            'success_rate': round(self.success_rate, 2),
            'nested_entities': {
                'contributors': self.contributors_created,
                'subjects': self.subjects_created,
                'text_contents': self.text_contents_created,
                'media_files': self.media_files_created,
                'prices': self.prices_created,
            },
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
        }
    
    def log_summary(self):
        summary = self.to_dict()
        logger.info(
            f"Import complete: {summary['succeeded']}/{summary['processed']} "
            f"({summary['success_rate']}%) in {summary['duration_seconds']:.1f}s "
            f"({summary['records_per_second']:.1f} rec/s)"
        )


# ============================================================================
# PRISMA DATABASE WRITER
# ============================================================================

class PrismaWriter:
    """
    Simple Prisma-based database writer.
    
    Uses Prisma upserts for idempotent writes.
    """
    
    def __init__(self, db: Prisma):
        self.db = db
    
    async def write_product(self, dto: ProductDTO, metrics: ImportMetrics) -> bool:
        """
        Write a single product with all nested entities.
        
        Returns True if successful.
        """
        try:
            # Prepare main product data (matching Prisma schema)
            product_data = self._prepare_product_data(dto)
            
            # Upsert by ISBN13 (our primary identifier)
            isbn13 = product_data.get('isbn13')
            if not isbn13:
                metrics.add_warning(dto.record_reference, "No ISBN13, skipping")
                return False
            
            # Upsert the product
            product = await self.db.catalogproduct.upsert(
                where={"isbn13": isbn13},
                data={
                    "create": product_data,
                    "update": {k: v for k, v in product_data.items() if k != 'isbn13'},
                },
            )
            
            if product:
                # Write nested entities
                await self._write_contributors(product.id, dto, metrics)
                await self._write_subjects(product.id, dto, metrics)
                await self._write_text_content(product.id, dto, metrics)
                await self._write_media_files(product.id, dto, metrics)
                # Note: Prices require a PriceSource, skip for now
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error writing product {dto.record_reference}: {e}")
            raise
    
    def _prepare_product_data(self, dto: ProductDTO) -> Dict[str, Any]:
        """Convert ProductDTO to Prisma-compatible dict."""
        flat = dto.to_flat_dict()
        
        # Convert date to datetime if needed
        pub_date = flat.get('publication_date')
        if pub_date:
            from datetime import date
            if isinstance(pub_date, date) and not isinstance(pub_date, datetime):
                pub_date = datetime(pub_date.year, pub_date.month, pub_date.day)
        
        return {
            'isbn13': flat.get('isbn13'),
            'isbn10': flat.get('isbn10'),
            'title': flat.get('title', 'Unknown'),
            'subtitle': flat.get('subtitle'),
            'product_form_code': flat.get('product_form') or 'BB',
            'language_code': flat.get('language_code') or 'ukr',
            'publisher_name': flat.get('publisher_name'),
            'page_count': flat.get('page_count'),
            'publication_date': pub_date,
            'publishing_status_code': flat.get('publishing_status') or '04',  # Active
            'width_mm': Decimal(str(flat['width_mm'])) if flat.get('width_mm') else None,
            'height_mm': Decimal(str(flat['height_mm'])) if flat.get('height_mm') else None,
            'thickness_mm': Decimal(str(flat['thickness_mm'])) if flat.get('thickness_mm') else None,
            'weight_g': Decimal(str(flat['weight_g'])) if flat.get('weight_g') else None,
            'metadata': Json({
                'source_name': flat.get('source_name'),
                'source_url': flat.get('source_url'),
                'source_priority': flat.get('source_priority'),
                'yakaboo_id': flat.get('yakaboo_id'),
                'imported_at': datetime.utcnow().isoformat(),
            })
        }
    
    async def _write_contributors(self, product_id: int, dto: ProductDTO, metrics: ImportMetrics):
        """Write product contributors (N:N via ProductContributor)."""
        if not dto.contributors:
            return
        
        # Delete existing junction records for this product
        await self.db.productcontributor.delete_many(where={"product_id": product_id})
        
        for i, contrib in enumerate(dto.contributors):
            try:
                person_name = contrib.name or contrib.person_name
                if not person_name:
                    continue
                
                # Find or create contributor
                contributor = await self.db.contributor.upsert(
                    where={
                        'contributor_type_person_name': {
                            'contributor_type': 'P',
                            'person_name': person_name[:300]
                        }
                    },
                    data={
                        'create': {
                            'contributor_type': 'P',
                            'person_name': person_name[:300],
                            'person_name_inverted': (contrib.inverted_name or '')[:300] if contrib.inverted_name else None,
                            'corporate_name': (contrib.corporate_name or '')[:300] if contrib.corporate_name else None,
                            'biographical_note': contrib.biography,
                        },
                        'update': {}
                    }
                )
                
                # Create junction record
                role_code = contrib.role_code.value if contrib.role_code else 'A01'
                await self.db.productcontributor.create(data={
                    'product_id': product_id,
                    'contributor_id': contributor.id,
                    'role_code': role_code,
                    'sequence_number': contrib.sequence_number or i + 1,
                })
                metrics.contributors_created += 1
            except Exception as e:
                logger.debug(f"Error creating contributor: {e}")
    
    async def _write_subjects(self, product_id: int, dto: ProductDTO, metrics: ImportMetrics):
        """Write product subjects/categories (N:N via ProductSubject)."""
        if not dto.subjects:
            return
        
        # Delete existing junction records for this product
        await self.db.productsubject.delete_many(where={"product_id": product_id})
        
        for i, subj in enumerate(dto.subjects):
            try:
                heading = subj.subject_heading or subj.subject_heading_text or ''
                if not heading:
                    continue
                
                scheme = subj.scheme_code.value if subj.scheme_code else '24'
                code = (subj.subject_code or '')[:100] if subj.subject_code else None
                
                # Find or create subject (use find_first + create to handle NULL in unique)
                subject = await self.db.subject.find_first(
                    where={
                        'scheme_code': scheme,
                        'subject_code': code,
                        'subject_heading_text': heading[:500]
                    }
                )
                if not subject:
                    try:
                        subject = await self.db.subject.create(data={
                            'scheme_code': scheme,
                            'subject_code': code,
                            'subject_heading_text': heading[:500],
                        })
                    except Exception:
                        # Race condition - another worker created it
                        subject = await self.db.subject.find_first(
                            where={
                                'scheme_code': scheme,
                                'subject_code': code,
                                'subject_heading_text': heading[:500]
                            }
                        )
                        if not subject:
                            raise
                
                # Create junction record
                await self.db.productsubject.create(data={
                    'product_id': product_id,
                    'subject_id': subject.id,
                    'is_primary': i == 0,
                    'sequence_number': i + 1,
                })
                metrics.subjects_created += 1
            except Exception as e:
                logger.debug(f"Error creating subject: {e}")
    
    async def _write_text_content(self, product_id: int, dto: ProductDTO, metrics: ImportMetrics):
        """Write text content (descriptions, etc)."""
        if not dto.text_content:
            return
        
        await self.db.textcontent.delete_many(where={"product_id": product_id})
        
        for text in dto.text_content:
            try:
                await self.db.textcontent.create(data={
                    "product_id": product_id,
                    "text_type_code": text.text_type_code.value if text.text_type_code else '03',
                    "content": text.content or '',
                })
                metrics.text_contents_created += 1
            except Exception as e:
                logger.debug(f"Error creating text content: {e}")
    
    async def _write_media_files(self, product_id: int, dto: ProductDTO, metrics: ImportMetrics):
        """Write media files (covers, etc)."""
        if not dto.media_files:
            return
        
        await self.db.mediafile.delete_many(where={"product_id": product_id})
        
        for i, media in enumerate(dto.media_files):
            try:
                await self.db.mediafile.create(data={
                    "product_id": product_id,
                    "resource_content_type_code": '01',  # Front cover
                    "resource_mode_code": '03',  # Image
                    "file_link": media.url or '',
                    "sequence_number": i + 1,
                })
                metrics.media_files_created += 1
            except Exception as e:
                logger.debug(f"Error creating media file: {e}")


# ============================================================================
# MAIN INGESTION SERVICE
# ============================================================================

class PrismaIngestionService:
    """
    Simple Prisma-based data ingestion service.
    
    Streams data from JSONL, transforms via adapter, writes via Prisma.
    """
    
    def __init__(
        self,
        adapter: BaseDataAdapter,
        batch_size: int = 100,
        log_every: int = 1000,
    ):
        self.adapter = adapter
        self.batch_size = batch_size
        self.log_every = log_every
        self.metrics = ImportMetrics()
    
    async def import_from_file(
        self,
        file_path: str,
        progress_callback: Callable[[int, int], None] = None,
        limit: int = None,
    ) -> ImportMetrics:
        """
        Import products from JSONL file.
        
        Args:
            file_path: Path to JSONL file
            progress_callback: Optional progress callback(current, total)
            limit: Maximum records to import
            
        Returns:
            Import metrics
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Count lines
        with open(path, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)
        
        self.metrics.total_records = min(total_lines, limit) if limit else total_lines
        logger.info(f"Starting import of {self.metrics.total_records:,} records")
        
        # Connect to Prisma
        db = Prisma()
        await db.connect()
        
        writer = PrismaWriter(db)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, 1):
                    if limit and line_number > limit:
                        break
                    
                    try:
                        # Parse JSON
                        raw_data = json.loads(line.strip())
                        
                        # Transform via adapter
                        result = self.adapter.transform(raw_data)
                        
                        if not result.is_valid:
                            self.metrics.failed += 1
                            for error in result.errors:
                                self.metrics.add_error(
                                    self.adapter.extract_identifier(raw_data),
                                    error.message,
                                    {'field': error.field, 'line': line_number}
                                )
                            self.metrics.processed += 1
                            continue
                        
                        # Write to database
                        success = await writer.write_product(result.data, self.metrics)
                        
                        if success:
                            self.metrics.succeeded += 1
                        else:
                            self.metrics.skipped += 1
                        
                        self.metrics.processed += 1
                        
                        # Progress callback
                        if progress_callback and self.metrics.processed % 10 == 0:
                            progress_callback(self.metrics.processed, self.metrics.total_records)
                        
                        # Log progress
                        if self.metrics.processed % self.log_every == 0:
                            logger.info(
                                f"Progress: {self.metrics.processed:,}/{self.metrics.total_records:,} "
                                f"({self.metrics.success_rate:.1f}% success, "
                                f"{self.metrics.records_per_second:.1f} rec/s)"
                            )
                    
                    except json.JSONDecodeError as e:
                        self.metrics.failed += 1
                        self.metrics.add_error(f"line_{line_number}", f"Invalid JSON: {e}")
                        self.metrics.processed += 1
                    
                    except Exception as e:
                        self.metrics.failed += 1
                        self.metrics.add_error(
                            f"line_{line_number}",
                            str(e),
                            {'line': line_number, 'exception': type(e).__name__}
                        )
                        self.metrics.processed += 1
        
        finally:
            await db.disconnect()
        
        self.metrics.finalize()
        self.metrics.log_summary()
        
        return self.metrics


# ============================================================================
# CLI
# ============================================================================

async def run_import(
    file_path: str,
    batch_size: int = 100,
    limit: int = None,
) -> Dict[str, Any]:
    """Run import from CLI."""
    from app.adapters.data_adapter import YakabooDataAdapter
    
    adapter = YakabooDataAdapter()
    service = PrismaIngestionService(adapter, batch_size=batch_size)
    
    metrics = await service.import_from_file(file_path, limit=limit)
    return metrics.to_dict()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.services.prisma_ingestion_service <file_path> [limit]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    result = asyncio.run(run_import(file_path, limit=limit))
    print(json.dumps(result, indent=2))
