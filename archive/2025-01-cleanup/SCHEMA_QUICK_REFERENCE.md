================================================================
SCHEMA REBUILD — QUICK REFERENCE
================================================================

📋 WHAT'S NEW:
  ✓ Prisma schema (schema_new.prisma) — 11 tables + 7 code lists
  ✓ SQL migrations (001, 002) — Create schema + seed codes
  ✓ SQLAlchemy models (catalog_new.py) — Async ORM, ready to use
  ✓ Migration script (migrate_schema_new.py) — Data transfer
  ✓ Guides (MIGRATION_GUIDE.md, SCHEMA_REBUILD_COMPLETE.md)

================================================================
FILES CREATED
================================================================

prisma/schema_new.prisma                      488 lines (Prisma schema)
prisma/migrations/001_create_base_schema.sql  320 lines (Schema + indexes)
prisma/migrations/002_seed_code_lists.sql     220 lines (ONIX codes)
app/models/catalog_new.py                     580 lines (SQLAlchemy ORM)
scripts/migrate_schema_new.py                 380 lines (Data migration)
SCHEMA_REBUILD_COMPLETE.md                    500 lines (This summary)
MIGRATION_GUIDE.md                            420 lines (Step-by-step)

================================================================
QUICK START (For Impatient)
================================================================

# 1. Backup (CRITICAL!)
pg_dump -U onix_user -d onix_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Create schema
psql -U onix_user -d onix_db -f prisma/migrations/001_create_base_schema.sql
psql -U onix_user -d onix_db -f prisma/migrations/002_seed_code_lists.sql

# 3. Rename old tables
psql -U onix_user -d onix_db << 'EOF'
ALTER TABLE catalog_products RENAME TO OLD_catalog_products;
ALTER TABLE contributors RENAME TO OLD_contributors;
ALTER TABLE subjects RENAME TO OLD_subjects;
ALTER TABLE text_content RENAME TO OLD_text_content;
ALTER TABLE media_files RENAME TO OLD_media_files;
EOF

# 4. Migrate data
export DATABASE_URL="postgresql+asyncpg://onix_user:pass@localhost/onix_db"
python scripts/migrate_schema_new.py

# 5. Verify
psql -U onix_user -d onix_db << 'EOF'
SELECT 'Products' as table_name,
  (SELECT COUNT(*) FROM catalog_products) as new,
  (SELECT COUNT(*) FROM OLD_catalog_products) as old
UNION ALL
SELECT 'Contributors',
  (SELECT COUNT(*) FROM contributors),
  (SELECT COUNT(*) FROM OLD_contributors);
EOF

# 6. Update app code
# - Replace imports: from app.models.catalog import → from app.models.catalog_new import
# - Add deleted_at filter to queries
# - Run tests: pytest tests/ -v

# 7. Deploy & monitor
pytest tests/ -v
python main.py  # or gunicorn/uvicorn

# 8. After 1 week (if stable): drop old tables
psql -U onix_user -d onix_db << 'EOF'
DROP TABLE OLD_catalog_products CASCADE;
DROP TABLE OLD_contributors CASCADE;
DROP TABLE OLD_subjects CASCADE;
DROP TABLE OLD_text_content CASCADE;
DROP TABLE OLD_media_files CASCADE;
VACUUM FULL;
EOF

================================================================
SCHEMA STRUCTURE (NEW)
================================================================

catalog_products (1M rows)
  ├── id (BigInt PK)
  ├── isbn13, isbn10, gtin14, proprietary_id
  ├── title, subtitle, collection_title, part_number
  ├── product_form_code (BA, BB, EA, EB, FA, FB, etc.)
  ├── page_count, width_mm, height_mm, thickness_mm, weight_g
  ├── language_code (ukr, eng, etc.)
  ├── publisher_name, imprint_name
  ├── publishing_status_code (00-09)
  ├── publication_date
  ├── audience_code, audience_range_from, audience_range_to
  ├── udc_code, bbk_code, dk_018_code (Ukrainian classification)
  ├── embedding (vector(1536) for semantic search)
  ├── metadata (JSONB)
  ├── created_at, updated_at, deleted_at (soft delete), is_active
  └── Relations:
      ├── contributors (1:N)
      ├── subjects (1:N)
      ├── text_content (1:N)
      ├── media_files (1:N)
      ├── prices (1:N)
      ├── sales_rights (1:N)
      └── related_products (N:N)

contributors (2-3 per book)
  ├── id, product_id (FK → catalog_products)
  ├── role_code (A01=Author, A14=Illustrator, B06=Translator, etc.)
  ├── sequence_number (1=primary author)
  ├── contributor_type (P=Person, C=Corporate)
  ├── person_name, key_names, names_before_key
  ├── corporate_name
  ├── biographical_note
  └── created_at

subjects (5-10 per book)
  ├── id, product_id (FK)
  ├── scheme_code (BISAC, BIC, Thema, UDC, BBK, DK-018, keywords)
  ├── subject_code, subject_heading_text
  ├── is_primary (Bool)
  ├── sequence_number

text_content (descriptions, reviews, excerpts)
  ├── id, product_id (FK)
  ├── text_type_code (01=Main desc, 02=Short desc, 23=Excerpt, etc.)
  ├── content (Text)
  ├── author, source_title
  └── created_at

media_files (cover images, video, etc.)
  ├── id, product_id (FK)
  ├── resource_content_type_code (01=Front cover, 02=Back cover, etc.)
  ├── resource_mode_code (03=Image, 06=Video, 07=Audio)
  ├── file_link (URL)
  ├── file_format_code (02=GIF, 03=JPEG, 05=PNG, 38=MP4)
  ├── width_px, height_px, file_size_bytes
  └── sequence_number

price_sources (retailers)
  ├── id (PK)
  ├── source_code (yakaboo, book24, balka, own_stock)
  ├── source_name, source_type
  ├── api_endpoint
  └── is_active (Bool)

prices (PARTITIONED by month)
  ├── id, product_id (FK), source_id (FK)
  ├── price_type_code (01=RRP, 02=Agency, 03=Wholesale, 41=Promo)
  ├── price_amount, currency_code (UAH)
  ├── tax_type_code, tax_rate_percent, tax_amount
  ├── discount_percent, stock_quantity
  ├── recorded_at (partition key) — 12 monthly partitions
  └── Materialized View: current_prices (refreshed 6-hourly)

sales_rights
  ├── id, product_id (FK)
  ├── sales_rights_type_code (01=For sale, 02=Not for sale)
  ├── territory_countries (Array: ['UA', 'PL', 'DE'])
  ├── territory_regions (Array)
  └── start_date, end_date

related_products (links between products)
  ├── id, product_id (FK), related_product_id (FK)
  └── relation_code (01=Alternative format, 06=Alternative, etc.)

Code lists (immutable reference data)
  ├── code_list_product_form (20 codes)
  ├── code_list_publishing_status (10 codes)
  ├── code_list_contributor_role (17 codes)
  ├── code_list_price_type (9 codes)
  ├── code_list_text_type (21 codes)
  ├── code_list_audience (8 codes)
  └── code_list_subject_scheme (8 schemes)

audit_log (change tracking)
  ├── id, table_name, record_id, operation (INSERT/UPDATE/DELETE)
  ├── old_data (JSONB), new_data (JSONB)
  ├── changed_by, changed_at

================================================================
KEY INDEXES (25+)
================================================================

Performance-critical:
  ✓ idx_products_isbn13 (UNIQUE) — lookup by ISBN
  ✓ idx_products_status — filter by publishing status
  ✓ idx_products_form — filter by product type
  ✓ idx_prices_product, idx_prices_source — price queries
  ✓ idx_subjects_primary — find main category
  ✓ idx_current_prices_unique — materialized view lookup

Search:
  ✓ idx_products_title_trgm (GIN) — fuzzy title search
  ✓ idx_contributors_name_trgm (GIN) — fuzzy author search
  ✓ idx_products_embedding (IVFFLAT) — vector similarity search

Reference data:
  ✓ idx_subjects_scheme — lookup by classification scheme
  ✓ idx_media_type — filter by media type

Soft delete:
  ✓ idx_products_deleted — find only active records

================================================================
QUERY EXAMPLES
================================================================

# Find product by ISBN
SELECT * FROM catalog_products
WHERE isbn13 = '9786177668171'
  AND deleted_at IS NULL;

# Get product with all relations
SELECT p.*, c.*, s.*, tc.*, m.*
FROM catalog_products p
LEFT JOIN contributors c ON p.id = c.product_id
LEFT JOIN subjects s ON p.id = s.product_id
LEFT JOIN text_content tc ON p.id = tc.product_id
LEFT JOIN media_files m ON p.id = m.product_id
WHERE p.isbn13 = '9786177668171'
  AND p.deleted_at IS NULL;

# Current price from all sources
SELECT cp.product_id, ps.source_name, cp.price_amount, cp.currency_code
FROM current_prices cp
JOIN price_sources ps ON cp.source_id = ps.id
WHERE cp.product_id = 12345
ORDER BY cp.price_amount;

# Semantic search (after backfill)
SELECT id, title, (1 - (embedding <-> query_embedding)) as similarity
FROM catalog_products
WHERE deleted_at IS NULL
ORDER BY embedding <-> query_embedding
LIMIT 10;

# Books by author
SELECT p.id, p.title, c.person_name
FROM catalog_products p
JOIN contributors c ON p.id = c.product_id
WHERE c.person_name ILIKE '%Шевченко%'
  AND c.role_code = 'A01'
  AND p.deleted_at IS NULL;

# Price history for product
SELECT recorded_at, price_amount, stock_quantity
FROM prices
WHERE product_id = 12345
ORDER BY recorded_at DESC
LIMIT 30;

================================================================
MIGRATION CHECKLIST
================================================================

PRE-MIGRATION:
  ☐ Backup: pg_dump complete
  ☐ Staging: Test environment ready
  ☐ Review: MIGRATION_GUIDE.md read
  ☐ Notify: Stakeholders informed
  ☐ Window: Downtime scheduled

MIGRATION:
  ☐ Schema: 001, 002 executed without errors
  ☐ Old tables: Renamed to OLD_*
  ☐ Data: migrate_schema_new.py completed
  ☐ Validation: Count checks match (±1%)
  ☐ FK validation: No orphaned records

APPLICATION UPDATE:
  ☐ Imports: catalog_new models imported
  ☐ Filters: deleted_at added to queries
  ☐ Tests: pytest passes (25+)
  ☐ Swagger: http://localhost:8000/docs works
  ☐ Sample: curl test successful

DEPLOYMENT:
  ☐ Staging: All endpoints work
  ☐ Load: 1000 req/s test passed
  ☐ Logs: Zero errors
  ☐ Monitoring: Dashboards ready
  ☐ Production: Deployed + stable

POST-MIGRATION:
  ☐ Monitoring: 24h clean operation
  ☐ Performance: Queries <100ms p95
  ☐ Data: No data loss detected
  ☐ Old tables: Can be dropped
  ☐ Success: Declared!

================================================================
PERFORMANCE EXPECTATIONS (1M books)
================================================================

Query type                          Time (p95)    Index used
────────────────────────────────────────────────────────────
SELECT by ISBN13                    <5ms          idx_products_isbn13
List products (pagination)          <50ms         idx_products_status
Get product + relations             <100ms        FK joinedload
Fuzzy search (ILIKE)                <200ms        idx_*_trgm
Semantic search (vector)            <200ms        idx_products_embedding
Current price lookup                <10ms         current_prices view
Contributor list by role            <50ms         idx_contributors_role
Subject query by scheme              <50ms         idx_subjects_scheme

Storage (for 1M books):
  Database: ~4-5 GB
  Indexes: ~500 MB
  Backups (30 days): ~150-200 GB
  Total with overhead: ~5-6 GB (production)

================================================================
TROUBLESHOOTING QUICK FIXES
================================================================

❌ "relation does not exist" → Schema not created
   → Run: 001, 002 migrations again

❌ "Foreign key violation" → Data has orphaned records
   → Check: SELECT * FROM contributors WHERE product_id NOT IN (...)
   → Fix: Clean or update migrate_schema_new.py

❌ "permission denied" → User doesn't have privileges
   → Check: GRANT SELECT, INSERT, UPDATE ON ALL TABLES TO onix_user;

❌ Embedding queries fail → pgvector not installed
   → Check: SELECT * FROM pg_extension WHERE extname = 'vector';
   → Fix: CREATE EXTENSION vector;

❌ Old tables still exists → Forgot to rename before migration
   → Rename: ALTER TABLE catalog_products RENAME TO OLD_catalog_products;
   → Rerun: python scripts/migrate_schema_new.py

❌ App can't find models → Wrong import path
   → Fix: from app.models.catalog_new import CatalogProduct
   → Clear: rm -rf __pycache__

================================================================
NEXT STEPS
================================================================

Immediate (after migration):
  1. Monitor logs for 24 hours
  2. Verify data integrity (spot-check 10 products)
  3. Test API endpoints (Swagger http://localhost:8000/docs)
  4. Run performance baseline

Short-term (week 1-2):
  1. Drop old tables (when confident)
  2. Implement semantic search (backfill embeddings)
  3. Set up price tracking dashboard

Medium-term (month 1-3):
  1. Build admin panel (manage codes, audit logs)
  2. Implement data validation (webhook from retailers)
  3. Optimize slow queries (add more indexes if needed)

Long-term (quarter 2-4):
  1. Scale to multi-region (read replicas)
  2. Analytics pipeline (dbt, Redash)
  3. Marketplace integration (price sync automation)

================================================================
NEED HELP?
================================================================

Schema questions:
  → docs/DB_SCHEMA.md (detailed table descriptions)

Migration issues:
  → MIGRATION_GUIDE.md (step-by-step + troubleshooting)

Query syntax:
  → docs/PRISMA_GUIDE.md (examples)

API design:
  → docs/API_IMPLEMENTATION_20250106.md (endpoints)

Performance tuning:
  → docs/DB_LOADERS_GUIDE.md (optimization)

================================================================
STATUS: 🟢 READY FOR MIGRATION

Review MIGRATION_GUIDE.md before executing!

Created: 2025-01-09
Version: 2.0 (ONIX 3.0 Normalized)
================================================================
