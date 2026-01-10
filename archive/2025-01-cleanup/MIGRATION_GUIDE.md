"""
MIGRATION EXECUTION GUIDE
Schema Rebuild: Old → New (ONIX 3.0 Normalized)

Timeline:
  1. Backup current database
  2. Create new schema (001, 002 migrations)
  3. Migrate data (optional: import fresh if starting over)
  4. Validate data integrity
  5. Update application layer (models, services, routers)
  6. Deploy + test
  7. Drop old tables (after confirming new is working)

Files Created:
  ✓ prisma/schema_new.prisma       — New Prisma schema
  ✓ prisma/migrations/001_*.sql    — Base schema + indexes
  ✓ prisma/migrations/002_*.sql    — Code lists seed
  ✓ app/models/catalog_new.py      — SQLAlchemy models (async)
  ✓ scripts/migrate_schema_new.py   — Data migration script
  ✓ MIGRATION_GUIDE.md              — This file

================================================================
STEP 1: BACKUP
================================================================

$ pg_dump -U onix_user -d onix_db > onix_backup_$(date +%Y%m%d_%H%M%S).sql

(Keep backup for rollback if needed)

================================================================
STEP 2: CREATE NEW SCHEMA
================================================================

$ psql -U onix_user -d onix_db -f prisma/migrations/001_create_base_schema.sql

Check for errors:
  - Should see "CREATE TABLE" and "CREATE INDEX" messages
  - No errors for "NOTICE: extension already exists"

$ psql -U onix_user -d onix_db -f prisma/migrations/002_seed_code_lists.sql

Verify code lists created:
  $ psql -U onix_user -d onix_db -c "SELECT COUNT(*) FROM code_list_product_form;"
  -> Should be ~20

================================================================
STEP 3A: RENAME OLD TABLES (for safety during migration)
================================================================

$ psql -U onix_user -d onix_db << 'EOF'

-- Rename old tables to OLD_* prefix
ALTER TABLE catalog_products RENAME TO OLD_catalog_products;
ALTER TABLE contributors RENAME TO OLD_contributors;
ALTER TABLE subjects RENAME TO OLD_subjects;
ALTER TABLE text_content RENAME TO OLD_text_content;
ALTER TABLE media_files RENAME TO OLD_media_files;

-- Keep price tables separate (or migrate independently)
-- ALTERtable prices RENAME TO OLD_prices;
-- ALTER TABLE price_sources RENAME TO OLD_price_sources;

EOF

================================================================
STEP 3B: RUN DATA MIGRATION (Python)
================================================================

# Set env vars
export DATABASE_URL="postgresql+asyncpg://onix_user:onix_pass@localhost:5432/onix_db"

# Run migration script
$ python scripts/migrate_schema_new.py

Expected output:
  ✅ Migrated 897918 core products
  ✅ Migrated 113 contributors
  ✅ Migrated 15234 subjects
  ✅ Migrated 8932 text content
  ✅ Migrated 12430 media files

Monitor progress:
  $ tail -f migration.log

================================================================
STEP 4: VALIDATE DATA INTEGRITY
================================================================

# Check row counts match
$ psql -U onix_user -d onix_db << 'EOF'

SELECT 
  'Products' as table_name,
  (SELECT COUNT(*) FROM catalog_products) as new_count,
  (SELECT COUNT(*) FROM OLD_catalog_products) as old_count
UNION ALL
SELECT 'Contributors',
  (SELECT COUNT(*) FROM contributors),
  (SELECT COUNT(*) FROM OLD_contributors)
UNION ALL
SELECT 'Subjects',
  (SELECT COUNT(*) FROM subjects),
  (SELECT COUNT(*) FROM OLD_subjects);

EOF

# Check foreign key integrity
$ psql -U onix_user -d onix_db << 'EOF'

-- Products without valid ISBN13 (if applicable)
SELECT COUNT(*) as orphan_isbn FROM catalog_products WHERE isbn13 IS NULL;

-- Contributors with no product
SELECT COUNT(*) as orphan_contributors 
FROM contributors c 
WHERE NOT EXISTS (SELECT 1 FROM catalog_products p WHERE p.id = c.product_id);

-- Test a random product with its relations
SELECT p.id, p.title, COUNT(c.id) as contributor_count
FROM catalog_products p
LEFT JOIN contributors c ON p.id = c.product_id
WHERE p.isbn13 IS NOT NULL
GROUP BY p.id, p.title
LIMIT 5;

EOF

================================================================
STEP 5: UPDATE APPLICATION LAYER
================================================================

5a. Update database module (app/core/database.py):
    - Replace old model imports with new models
    - Use app/models/catalog_new.py as CatalogProduct, etc.

5b. Update repositories (app/repositories/product_repository.py):
    - Use new model relations
    - Example: product.contributors instead of separate join query
    - Update query logic for deleted_at filter

5c. Update services (app/services/catalog_service.py):
    - Map new models → DTOs
    - Use embedded relations (from ORM)
    - No major changes needed if DTOs are same

5d. Update routers (app/routers/catalog.py):
    - Endpoint logic usually unchanged
    - May need to update query filters

Example before/after:

BEFORE (old model):
  query = select(OLD_CatalogProduct).where(
    OLD_CatalogProduct.isbn13 == isbn13
  ).options(joinedload(OLD_CatalogProduct.contributors))

AFTER (new model):
  query = select(CatalogProduct).where(
    CatalogProduct.isbn13 == isbn13,
    CatalogProduct.deleted_at.is_(None)
  ).options(selectinload(CatalogProduct.contributors))

================================================================
STEP 6: RUN TESTS
================================================================

$ pytest tests/ -v

Expected:
  - 25+ tests pass
  - No import errors from new models
  - DTOs still match endpoints

If tests fail:
  1. Check model imports
  2. Verify foreign key relationships
  3. Check query filters (deleted_at added)

================================================================
STEP 7: DEPLOY TO STAGING
================================================================

1. Deploy code changes (models, services, routers)
2. Test endpoints:
   $ curl http://localhost:8000/api/v1/products?page=1&limit=10
   
3. Check Swagger docs: http://localhost:8000/docs

4. Run integration tests against staging DB

5. Monitor logs for errors

================================================================
STEP 8: DROP OLD TABLES (only after confident new is working)
================================================================

# After 1-2 weeks of successful operation on new schema:

$ psql -U onix_user -d onix_db << 'EOF'

-- Check if new tables have data
SELECT COUNT(*) FROM catalog_products;
-- Should be > 890000

-- Drop old tables (CAREFUL!)
DROP TABLE IF EXISTS OLD_catalog_products CASCADE;
DROP TABLE IF EXISTS OLD_contributors CASCADE;
DROP TABLE IF EXISTS OLD_subjects CASCADE;
DROP TABLE IF EXISTS OLD_text_content CASCADE;
DROP TABLE IF EXISTS OLD_media_files CASCADE;

-- Verify space freed
VACUUM FULL ANALYZE;

EOF

================================================================
STEP 9: ONGOING MAINTENANCE
================================================================

Refresh materialized view (every 6 hours):
  $ psql -U onix_user -d onix_db -c "REFRESH MATERIALIZED VIEW CONCURRENTLY current_prices;"

Monitor partition sizes:
  $ psql -U onix_user -d onix_db -c "
    SELECT 
      schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
    FROM pg_tables 
    WHERE tablename LIKE 'prices_%' 
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

Auto-create monthly partitions (set up cron):
  # Add to crontab (runs 1st of each month)
  0 0 1 * * psql -U onix_user -d onix_db -c "SELECT create_price_partition();"

Audit trail:
  $ psql -U onix_user -d onix_db -c "
    SELECT changed_at, operation, COUNT(*) FROM audit_log 
    GROUP BY changed_at, operation 
    ORDER BY changed_at DESC LIMIT 10;"

================================================================
ROLLBACK PLAN (if needed)
================================================================

If new schema has issues:

1. Stop application
2. Restore from backup:
   $ psql -U onix_user -d onix_db < onix_backup_20250109_120000.sql
3. Revert code changes (git checkout)
4. Restart application

Estimated downtime: ~30 minutes (depending on backup size)

================================================================
TROUBLESHOOTING
================================================================

Q: Migration script hangs after 10000 products
A: Check DB memory. Query plan might be inefficient.
   - Restart script with --resume flag (when implemented)
   - Reduce batch size in migrate_schema_new.py

Q: Foreign key constraint errors during migration
A: One table referencing non-existent record
   - Check orphaned records in old tables
   - Run: SELECT COUNT(*) FROM contributors WHERE product_id NOT IN (SELECT id FROM catalog_products);
   - Fix by cleaning old data before re-running migration

Q: New tables created but no data migrated
A: Python script failed silently
   - Check migration.log for errors
   - Run migrate_schema_new.py with verbose flag (add logging)
   - Manually inspect old tables: SELECT COUNT(*) FROM OLD_catalog_products;

Q: Application can't find models after deploy
A: Import paths wrong or models not reloaded
   - Ensure app/models/catalog_new.py is imported in __init__.py
   - Clear __pycache__ and reinstall requirements
   - Check DATABASE_URL in .env

Q: Semantic search (embedding) queries fail
A: pgvector extension not loaded, or embedding column is NULL
   - Run: SELECT * FROM catalog_products LIMIT 1 WHERE embedding IS NOT NULL;
   - If 0 rows: backfill embeddings (separate process)
   - Check: CREATE EXTENSION IF NOT EXISTS vector; in migration

================================================================
SUCCESS CRITERIA
================================================================

✅ New schema created, 0 errors
✅ Data migrated: counts match old tables (±1%)
✅ Foreign keys valid: no orphaned records
✅ Tests pass: 25+ passing
✅ Endpoints work: GET /api/v1/products returns data
✅ Performance acceptable: queries < 500ms for 1M rows
✅ No errors in logs: clean startup, no warnings

When all ✅, you have successfully rebuilt the base!

================================================================
NEXT STEPS (After Migration)
================================================================

1. Implement semantic search (embedding backfill)
2. Set up price tracking (auto-refresh current_prices view)
3. Build admin panel (manage code lists, audit logs)
4. Implement data validation (webhook from retailers)
5. Scale to multi-region (read replicas)

Questions? Check docs/:
  - DB_SCHEMA.md — table relationships
  - PRISMA_GUIDE.md — query examples
  - API_IMPLEMENTATION_20250106.md — endpoint design
