-- Enable pgvector and pgai extensions
-- Run once on the database as a superuser or a user with CREATE privilege on extensions.

CREATE EXTENSION IF NOT EXISTS vector;
-- pgai is optional; available on some Postgres builds (e.g., Supabase). If unavailable, this will fail harmlessly when run manually.
DO $$ BEGIN
  CREATE EXTENSION IF NOT EXISTS ai;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'pgai extension not available on this server';
END $$;

-- Recommended index for products table if not already present
-- CREATE INDEX IF NOT EXISTS idx_products_embedding ON products USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- Recommended index for catalog_products
-- CREATE INDEX IF NOT EXISTS idx_catalog_products_embedding ON catalog_products USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
