# PRISMA & DATABASE (KNOWLEDGE BASE)

## OVERVIEW
The database layer uses **PostgreSQL** managed through **Prisma ORM**. It serves as the source of truth for normalized book data, price history, and ETL ingestion logs. The architecture supports a multi-schema approach (`public` for normalized data, `cold` for raw staging).

## SCHEMA HIGHLIGHTS

### Key Tables
- **Product (`public.products`)**: Central entity for normalized data.
    - **Identity**: Unique composite key on `(source_name, external_id)`.
    - **Optimization**: `content_hash` (SHA256) used in UPSERTs to prevent unnecessary writes if data hasn't changed.
    - **Persistence**: `rawData` (JSONB) stores the original source response for future re-parsing.
- **PriceHistory (`public.price_history`)**: Stores delta price points.
    - **Relation**: Many-to-One with `Product`.
    - **Constraint**: `onDelete: Cascade` — history is wiped if the product is deleted.
- **IngestionLog (`public.ingestion_logs`)**: Tracks status of ETL runs (`pending`, `processing`, `completed`, `failed`).

### External Schemas (Non-Prisma managed)
- **Cold Schema (`cold`)**: Staging area for raw payloads.
- **Fact Schema (`fact`)**: Granular data layers for identifiers, titles, and contributors.
> **Note**: These schemas are currently defined via manual SQL migrations (`003_cold_fact_layers`) and are not yet fully mapped in `schema.prisma`.

## MIGRATION GUIDE

### Standard Flow
1. Modify `prisma/schema.prisma`.
2. Generate migration: `npx prisma migrate dev --name <description>`.
3. Update clients: `prisma generate` (updates both JS and Python clients).

### Safe Updates for Large Tables
- **Adding Columns**: For the `products` table (millions of rows), add new columns as nullable or with a default to avoid long-running exclusive locks.
- **Adding Indexes**: If adding indexes manually in `migration.sql`, consider using `CREATE INDEX CONCURRENTLY` to avoid blocking writes.

## ANTI-PATTERNS

- **Manual DB Modification**: NEVER run `ALTER TABLE` or `CREATE TABLE` directly in the database. Use migrations.
- **Bypassing the Hash**: NEVER update `products` without checking the `content_hash`. This project relies on hash-based change detection to keep `PriceHistory` clean.
- **Raw SQL for CRUD**: Avoid `db.query_raw` for standard selects or inserts. Use it ONLY for high-performance UPSERT logic or complex analytical queries.
- **Ignoring Generation**: Forgetting to run `prisma generate` after a schema change will cause type errors in the Python ETL worker.
