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
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field

# pyright: reportArgumentType=false
# pyright: reportCallIssue=false
# pyright: reportAttributeAccessIssue=false
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from prisma import Prisma
from prisma import Json

# NOTE: Prisma Python client typing is stricter than runtime behavior,
# so some Prisma calls below use type: ignore to avoid false positives.

from app.core.prisma_db import prisma as shared_db
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

    # Gatekeeper skip reason counters
    skipped_not_book: int = 0
    skipped_non_ukr: int = 0
    skipped_missing_name: int = 0
    skipped_missing_isbn: int = 0
    skipped_filtered_other: int = 0

    contributors_created: int = 0
    subjects_created: int = 0
    text_contents_created: int = 0
    media_files_created: int = 0
    prices_created: int = 0

    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def add_error(
        self, record_id: str, error: str, details: Optional[Dict[str, Any]] = None
    ):
        self.errors.append(
            {
                "record_id": record_id,
                "error": error,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        if len(self.errors) > 1000:
            self.errors = self.errors[-500:]

    def add_warning(
        self, record_id: str, warning: str, details: Optional[Dict[str, Any]] = None
    ):
        self.warnings.append(
            {
                "record_id": record_id,
                "warning": warning,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
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
            "duration_seconds": self.duration_seconds,
            "records_per_second": round(self.records_per_second, 2),
            "total_records": self.total_records,
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "duplicates": self.duplicates,
            "skipped_reasons": {
                "not_book": self.skipped_not_book,
                "non_ukr": self.skipped_non_ukr,
                "missing_name": self.skipped_missing_name,
                "missing_isbn": self.skipped_missing_isbn,
                "other": self.skipped_filtered_other,
            },
            "success_rate": round(self.success_rate, 2),
            "nested_entities": {
                "contributors": self.contributors_created,
                "subjects": self.subjects_created,
                "text_contents": self.text_contents_created,
                "media_files": self.media_files_created,
                "prices": self.prices_created,
            },
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }

    def log_summary(self):
        summary = self.to_dict()
        skipped_reasons = summary.get("skipped_reasons") or {}

        logger.info(
            f"Import complete: {summary['succeeded']}/{summary['processed']} "
            f"({summary['success_rate']}%) in {summary['duration_seconds']:.1f}s "
            f"({summary['records_per_second']:.1f} rec/s)"
        )
        logger.info(
            "Skipped: total=%s (not_book=%s, non_ukr=%s, missing_name=%s, missing_isbn=%s, other=%s)",
            summary.get("skipped"),
            skipped_reasons.get("not_book"),
            skipped_reasons.get("non_ukr"),
            skipped_reasons.get("missing_name"),
            skipped_reasons.get("missing_isbn"),
            skipped_reasons.get("other"),
        )


# ============================================================================
# PRISMA DATABASE WRITER
# ============================================================================


class PrismaWriter:
    """Prisma-based database writer.

    Uses Prisma upserts for idempotent writes.

    IMPORTANT: `write_product` is atomic (single transaction) and will rollback on
    any failure while writing nested entities.
    """

    def __init__(self, db: Prisma):
        self.db = db

    async def write_product(self, dto: ProductDTO, metrics: ImportMetrics) -> bool:
        """Write a single product with all nested entities.

        Returns:
            True if successful, False if skipped (e.g., missing ISBN13).

        All DB writes for a product run inside a single interactive transaction.
        """
        product_data = self._prepare_product_data(dto)

        isbn13 = product_data.get("isbn13")
        if not isbn13:
            metrics.add_warning(dto.record_reference, "No ISBN13, skipping")
            return False

        try:
            async with self.db.tx() as tx:
                # Prisma typing is stricter than runtime.
                # noqa: type checking mismatch

                # Prisma client typing mismatch; safe at runtime.
                # Prisma python client typing is stricter than runtime.
                product = await tx.catalogproduct.upsert(
                    where={"isbn13": isbn13},
                    data={
                        "create": product_data,
                        "update": {
                            k: v for k, v in product_data.items() if k != "isbn13"
                        },
                    },
                )

                await self._write_contributors(tx, product.id, dto, metrics)
                await self._write_subjects(tx, product.id, dto, metrics)
                await self._write_yakaboo_categories(tx, product.id, dto, metrics)
                await self._write_text_content(tx, product.id, dto, metrics)
                await self._write_media_files(tx, product.id, dto, metrics)

            return True

        except Exception:
            # Transaction should rollback automatically.
            logger.exception(
                "Error writing product (record_reference=%s, isbn13=%s)",
                dto.record_reference,
                isbn13,
            )
            raise

    def _prepare_product_data(self, dto: ProductDTO) -> Dict[str, Any]:
        """Convert ProductDTO to Prisma-compatible dict."""
        flat = dto.to_flat_dict()

        # Convert date to datetime if needed
        pub_date = flat.get("publication_date")
        if pub_date:
            from datetime import date

            if isinstance(pub_date, date) and not isinstance(pub_date, datetime):
                pub_date = datetime(pub_date.year, pub_date.month, pub_date.day)

        metadata = flat.get("metadata") or {}
        source = metadata.get("source") if isinstance(metadata, dict) else {}
        yakaboo = source.get("yakaboo") if isinstance(source, dict) else {}
        metrics = metadata.get("metrics") if isinstance(metadata, dict) else {}

        return {
            "isbn13": flat.get("isbn13"),
            "isbn10": flat.get("isbn10"),
            "gtin14": flat.get("gtin14"),
            "proprietary_id": flat.get("proprietary_id"),
            "title": flat.get("title", "Unknown"),
            "subtitle": flat.get("subtitle"),
            "collection_title": flat.get("collection_title"),
            "collection_issn": flat.get("collection_issn"),
            "part_number": flat.get("part_number"),
            "product_form_code": flat.get("product_form_code") or "BB",
            "product_form_detail_code": flat.get("product_form_detail_code"),
            "language_code": flat.get("language_code") or "ukr",
            "publisher_name": flat.get("publisher_name"),
            "publisher_id": flat.get("publisher_id"),
            "imprint_name": flat.get("imprint_name"),
            "audience_code": flat.get("audience_code"),
            "audience_range_qualifier": flat.get("audience_range_qualifier"),
            "audience_range_from": flat.get("audience_range_from"),
            "audience_range_to": flat.get("audience_range_to"),
            "primary_subject_scheme": flat.get("primary_subject_scheme"),
            "primary_subject_code": flat.get("primary_subject_code"),
            "udc_code": flat.get("udc_code"),
            "bbk_code": flat.get("bbk_code"),
            "dk_018_code": flat.get("dk_018_code"),
            "page_count": flat.get("page_count"),
            "publication_date": pub_date,
            "publishing_status_code": flat.get("publishing_status") or "04",  # Active
            "width_mm": Decimal(str(flat["width_mm"]))
            if flat.get("width_mm")
            else None,
            "height_mm": Decimal(str(flat["height_mm"]))
            if flat.get("height_mm")
            else None,
            "thickness_mm": Decimal(str(flat["thickness_mm"]))
            if flat.get("thickness_mm")
            else None,
            "weight_g": Decimal(str(flat["weight_g"]))
            if flat.get("weight_g")
            else None,
            # Source-normalized columns
            "source_name": source.get("name") if isinstance(source, dict) else None,
            "source_code": source.get("code") if isinstance(source, dict) else None,
            "yakaboo_id": yakaboo.get("id") if isinstance(yakaboo, dict) else None,
            "yakaboo_sku": yakaboo.get("sku") if isinstance(yakaboo, dict) else None,
            "yakaboo_url_key": yakaboo.get("url_key")
            if isinstance(yakaboo, dict)
            else None,
            "yakaboo_attribute_set_id": yakaboo.get("attribute_set_id")
            if isinstance(yakaboo, dict)
            else None,
            "yakaboo_statistics_visits": metrics.get("statistics_visits")
            if isinstance(metrics, dict)
            else None,
            "yakaboo_is_top_sale": metrics.get("is_top_sale")
            if isinstance(metrics, dict)
            else None,
            # Keep full metadata too
            "metadata": Json(
                {**metadata, "import": {"imported_at": datetime.utcnow().isoformat()}}
            ),
        }

    async def _write_contributors(
        self, tx: Prisma, product_id: int, dto: ProductDTO, metrics: ImportMetrics
    ):
        """Write product contributors (N:N via ProductContributor)."""
        if not dto.contributors:
            return

        # Delete existing junction records for this product
        await tx.productcontributor.delete_many(where={"product_id": product_id})

        for i, contrib in enumerate(dto.contributors):
            person_name = contrib.person_name
            if not person_name:
                continue

            # Find or create contributor
            contributor = await tx.contributor.upsert(
                where={
                    "contributor_type_person_name": {
                        "contributor_type": "P",
                        "person_name": person_name[:300],
                    }
                },
                data={
                    "create": {
                        "contributor_type": "P",
                        "person_name": person_name[:300],
                        "person_name_inverted": (contrib.person_name_inverted or "")[
                            :300
                        ]
                        if contrib.person_name_inverted
                        else None,
                        "corporate_name": (contrib.corporate_name or "")[:300]
                        if contrib.corporate_name
                        else None,
                        "biographical_note": contrib.biographical_note,
                    },
                    "update": {},
                },
            )

            # Create junction record
            role_code = contrib.role_code.value if contrib.role_code else "A01"
            await tx.productcontributor.create(
                data={
                    "product_id": product_id,
                    "contributor_id": contributor.id,
                    "role_code": role_code,
                    "sequence_number": contrib.sequence_number or i + 1,
                }
            )
            metrics.contributors_created += 1

    async def _write_subjects(
        self, tx: Prisma, product_id: int, dto: ProductDTO, metrics: ImportMetrics
    ):
        """Write product subjects/categories (N:N via ProductSubject)."""
        if not dto.subjects:
            return

        # Delete existing junction records for this product
        await tx.productsubject.delete_many(where={"product_id": product_id})

        seen_subject_keys: Set[tuple[str, Optional[str], str]] = set()
        for i, subj in enumerate(dto.subjects):
            heading = subj.subject_heading_text or ""
            if not heading:
                continue

            scheme = subj.scheme_code.value if subj.scheme_code else "24"
            code = (subj.subject_code or "")[:100] if subj.subject_code else None

            dedupe_key = (scheme, code, heading[:500])
            if dedupe_key in seen_subject_keys:
                continue
            seen_subject_keys.add(dedupe_key)

            # Find or create subject (use find_first + create to handle NULL in unique)
            subject = await tx.subject.find_first(
                where={
                    "scheme_code": scheme,
                    "subject_code": code,
                    "subject_heading_text": heading[:500],
                }
            )
            if not subject:
                try:
                    subject = await tx.subject.create(
                        data={
                            "scheme_code": scheme,
                            "subject_code": code,
                            "subject_heading_text": heading[:500],
                        }
                    )
                except Exception:
                    # Race condition - another worker created it
                    subject = await tx.subject.find_first(
                        where={
                            "scheme_code": scheme,
                            "subject_code": code,
                            "subject_heading_text": heading[:500],
                        }
                    )
                    if not subject:
                        raise

            # Create junction record
            await tx.productsubject.create(
                data={
                    "product_id": product_id,
                    "subject_id": subject.id,
                    "is_primary": i == 0,
                    "sequence_number": i + 1,
                }
            )
            metrics.subjects_created += 1

    async def _write_text_content(
        self, tx: Prisma, product_id: int, dto: ProductDTO, metrics: ImportMetrics
    ):
        """Write text content (descriptions, etc)."""
        if not dto.text_content:
            return

        await tx.textcontent.delete_many(where={"product_id": product_id})

        for text in dto.text_content:
            await tx.textcontent.create(
                data={
                    "product_id": product_id,
                    "text_type_code": text.text_type_code.value
                    if text.text_type_code
                    else "03",
                    "content": text.content or "",
                }
            )
            metrics.text_contents_created += 1

    async def _write_yakaboo_categories(
        self, tx: Prisma, product_id: int, dto: ProductDTO, metrics: ImportMetrics
    ):
        """Write Yakaboo category taxonomy links.

        Categories are sourced from adapter-provided metadata:
        metadata.source.yakaboo.category (list of category dicts)

        Idempotency strategy: replace all existing links for product.
        """
        metadata = dto.metadata or {}
        source = metadata.get("source") if isinstance(metadata, dict) else {}
        yakaboo = source.get("yakaboo") if isinstance(source, dict) else {}

        # Adapter currently stores just category ID list under metadata.catalog.category_ids.
        catalog = metadata.get("catalog") if isinstance(metadata, dict) else {}
        category_ids = (
            catalog.get("category_ids") if isinstance(catalog, dict) else None
        )
        if not isinstance(category_ids, list) or not category_ids:
            return

        categories = [{"id": cid} for cid in category_ids if isinstance(cid, int)]

        if not isinstance(categories, list) or not categories:
            return

        await tx.productyakaboocategory.delete_many(where={"product_id": product_id})

        seen_ids: Set[int] = set()
        for pos, cat in enumerate(categories):
            if not isinstance(cat, dict):
                continue

            cat_id = cat.get("id")
            if not isinstance(cat_id, int):
                continue
            if cat_id in seen_ids:
                continue
            seen_ids.add(cat_id)

            name = cat.get("name")
            if not isinstance(name, str) or not name.strip():
                name = f"Yakaboo Category {cat_id}"

            parent_id = cat.get("parent_id")
            if not isinstance(parent_id, int):
                parent_id = None

            level = cat.get("level")
            if not isinstance(level, int):
                level = None

            url_path = cat.get("url_path")
            if not isinstance(url_path, str) or not url_path.strip():
                url_path = None

            await tx.yakaboocategory.upsert(
                where={"id": cat_id},
                data={
                    "create": {
                        "id": cat_id,
                        "name": name[:500],
                        "parent_id": parent_id,
                        "level": level,
                        "url_path": url_path[:500] if url_path else None,
                    },
                    "update": {
                        "name": name[:500],
                        "parent_id": parent_id,
                        "level": level,
                        "url_path": url_path[:500] if url_path else None,
                    },
                },
            )

            await tx.productyakaboocategory.create(
                data={
                    "product_id": product_id,
                    "category_id": cat_id,
                    "position": pos + 1,
                    "is_primary": pos == 0,
                }
            )

    async def _write_media_files(
        self, tx: Prisma, product_id: int, dto: ProductDTO, metrics: ImportMetrics
    ):
        """Write media files (covers, etc)."""
        if not dto.media_files:
            return

        await tx.mediafile.delete_many(where={"product_id": product_id})

        for i, media in enumerate(dto.media_files):
            await tx.mediafile.create(
                data={
                    "product_id": product_id,
                    "resource_content_type_code": "01",  # Front cover
                    "resource_mode_code": "03",  # Image
                    "file_link": media.file_link or "",
                    "sequence_number": i + 1,
                }
            )
            metrics.media_files_created += 1


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
        progress_callback: Optional[Callable[[int, int], None]] = None,
        limit: Optional[int] = None,
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
        with open(path, "r", encoding="utf-8") as f:
            total_lines = sum(1 for _ in f)

        self.metrics.total_records = min(total_lines, limit) if limit else total_lines
        logger.info(f"Starting import of {self.metrics.total_records:,} records")

        db = shared_db
        raw_ingestion = getattr(db, "rawingestion", None) or getattr(
            db, "raw_ingestion", None
        )
        if raw_ingestion is None:
            logger.warning(
                "RawIngestion model not available on Prisma client; disabling cold.RawIngestion writes"
            )
        if not db.is_connected():
            try:
                await db.connect()
            except Exception as e:
                logger.error("Failed to connect to DB: %s", e)
                raise

        writer = PrismaWriter(db)

        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_number, line in enumerate(f, 1):
                    if limit and line_number > limit:
                        break

                    fingerprint = None
                    try:
                        raw_line = line.strip()
                        fingerprint = hashlib.sha256(
                            raw_line.encode("utf-8")
                        ).hexdigest()
                        raw_data = json.loads(raw_line)

                        allowed, reason = self.adapter.should_ingest_with_reason(
                            raw_data
                        )
                        if not allowed:
                            if reason == "not_book":
                                self.metrics.skipped_not_book += 1
                            elif reason == "non_ukr":
                                self.metrics.skipped_non_ukr += 1
                            elif reason == "missing_name":
                                self.metrics.skipped_missing_name += 1
                            elif reason == "missing_isbn":
                                self.metrics.skipped_missing_isbn += 1
                            else:
                                self.metrics.skipped_filtered_other += 1

                            logger.debug(
                                "Gatekeeper skip (reason=%s, line=%s)",
                                reason,
                                line_number,
                            )
                            self.metrics.skipped += 1
                            self.metrics.processed += 1
                            continue

                        existing = None
                        if raw_ingestion is not None:
                            existing = await raw_ingestion.find_unique(
                                where={"fingerprint": fingerprint}
                            )

                        if existing and existing.status == "PROCESSED":
                            logger.debug(
                                "Skipping duplicate raw payload (fingerprint=%s)",
                                fingerprint,
                            )
                            self.metrics.duplicates += 1
                            self.metrics.skipped += 1
                            self.metrics.processed += 1
                            continue

                        if raw_ingestion is not None:
                            await raw_ingestion.upsert(
                                where={"fingerprint": fingerprint},
                                data={
                                    "create": {
                                        "provider": self.adapter.source_code,
                                        "payload": Json(raw_data),
                                        "fingerprint": fingerprint,
                                        "status": "PENDING",
                                    },
                                    "update": {
                                        "provider": self.adapter.source_code,
                                        "payload": Json(raw_data),
                                        "status": "PENDING",
                                        "error": None,
                                    },
                                },
                            )

                        result = self.adapter.transform(raw_data)

                        if not result.is_valid:
                            self.metrics.failed += 1
                            for error in result.errors[:5]:
                                self.metrics.add_error(
                                    self.adapter.extract_identifier(raw_data)
                                    or fingerprint,
                                    error.message,
                                    {
                                        "field": error.field,
                                        "line": line_number,
                                        "value": getattr(error, "value", None),
                                        "path": getattr(error, "path", None),
                                        "raw_title": raw_data.get("title")
                                        if isinstance(raw_data, dict)
                                        else None,
                                    },
                                )
                            if raw_ingestion is not None:
                                await raw_ingestion.update(
                                    where={"fingerprint": fingerprint},
                                    data={
                                        "status": "FAILED",
                                        "error": "Validation failed",
                                    },
                                )
                            if self.metrics.failed <= 5:
                                logger.error(
                                    "Validation failed for line %s id=%s errors=%s",
                                    line_number,
                                    self.adapter.extract_identifier(raw_data)
                                    or fingerprint,
                                    [e.model_dump() for e in result.errors[:5]],
                                )
                            self.metrics.processed += 1
                            continue

                        if result.data is None:
                            raise ValueError(
                                "Adapter returned no data for valid result"
                            )
                        success = await writer.write_product(result.data, self.metrics)

                        if success:
                            self.metrics.succeeded += 1
                        else:
                            self.metrics.skipped += 1

                        self.metrics.processed += 1

                        if raw_ingestion is not None:
                            await raw_ingestion.update(
                                where={"fingerprint": fingerprint},
                                data={"status": "PROCESSED", "error": None},
                            )

                        if progress_callback and self.metrics.processed % 10 == 0:
                            progress_callback(
                                self.metrics.processed, self.metrics.total_records
                            )

                        if self.metrics.processed % self.log_every == 0:
                            logger.info(
                                f"Progress: {self.metrics.processed:,}/{self.metrics.total_records:,} "
                                f"({self.metrics.success_rate:.1f}% success, "
                                f"{self.metrics.records_per_second:.1f} rec/s)"
                            )

                    except json.JSONDecodeError as e:
                        self.metrics.failed += 1
                        self.metrics.add_error(
                            f"line_{line_number}", f"Invalid JSON: {e}"
                        )
                        self.metrics.processed += 1

                    except Exception as e:
                        self.metrics.failed += 1
                        self.metrics.add_error(
                            f"line_{line_number}",
                            str(e),
                            {"line": line_number, "exception": type(e).__name__},
                        )
                        if fingerprint and raw_ingestion is not None:
                            try:
                                await raw_ingestion.update(
                                    where={"fingerprint": fingerprint},
                                    data={"status": "FAILED", "error": str(e)[:5000]},
                                )
                            except Exception:
                                pass
                        self.metrics.processed += 1

        finally:
            # Do not disconnect global Prisma client here.
            # Connection lifecycle is managed by the application.
            pass

        self.metrics.finalize()
        self.metrics.log_summary()

        return self.metrics


# ============================================================================
# CLI
# ============================================================================


async def run_import(
    file_path: str,
    batch_size: int = 100,
    limit: Optional[int] = None,
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
        print(
            "Usage: python -m app.services.prisma_ingestion_service <file_path> [limit]"
        )
        sys.exit(1)

    file_path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None

    result = asyncio.run(run_import(file_path, limit=limit))
    print(json.dumps(result, indent=2))
