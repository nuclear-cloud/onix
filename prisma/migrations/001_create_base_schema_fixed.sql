-- ================================================================
-- 001_create_base_schema_fixed.sql
-- Create all core tables with proper dependency ordering
-- ================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- ================================================================
-- catalog_products (main table)
-- ================================================================

CREATE TABLE IF NOT EXISTS catalog_products (
  id BIGSERIAL PRIMARY KEY,
  isbn13 VARCHAR(13) UNIQUE,
  isbn10 VARCHAR(10),
  gtin14 VARCHAR(14),
  proprietary_id VARCHAR(100),
  
  title VARCHAR(500) NOT NULL,
  subtitle VARCHAR(500),
  
  collection_title VARCHAR(300),
  collection_issn VARCHAR(20),
  part_number VARCHAR(50),
  
  product_form_code CHAR(2) NOT NULL,
  product_form_detail_code VARCHAR(10),
  
  page_count INT,
  width_mm DECIMAL(6,2),
  height_mm DECIMAL(6,2),
  thickness_mm DECIMAL(6,2),
  weight_g DECIMAL(8,2),
  
  language_code CHAR(3) NOT NULL DEFAULT 'ukr',
  
  publisher_name VARCHAR(300),
  publisher_id VARCHAR(50),
  imprint_name VARCHAR(300),
  
  publishing_status_code CHAR(2) NOT NULL,
  publication_date DATE,
  out_of_print_date DATE,
  
  audience_code CHAR(2),
  audience_range_qualifier VARCHAR(10),
  audience_range_from INT,
  audience_range_to INT,
  
  primary_subject_scheme VARCHAR(10),
  primary_subject_code VARCHAR(50),
  
  udc_code VARCHAR(50),
  bbk_code VARCHAR(50),
  dk_018_code VARCHAR(20),
  
  embedding vector(1536),
  metadata JSONB,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT true,
  
  CONSTRAINT chk_isbn13 CHECK (isbn13 ~ '^[0-9]{13}$' OR isbn13 IS NULL)
);

CREATE INDEX idx_products_isbn13 ON catalog_products(isbn13);
CREATE INDEX idx_products_status ON catalog_products(publishing_status_code) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_publisher ON catalog_products(publisher_name);
CREATE INDEX idx_products_form ON catalog_products(product_form_code);
CREATE INDEX idx_products_language ON catalog_products(language_code);
CREATE INDEX idx_products_publication_date ON catalog_products(publication_date);
CREATE INDEX idx_products_metadata ON catalog_products USING GIN(metadata);
CREATE INDEX idx_products_deleted ON catalog_products(deleted_at);
CREATE INDEX idx_products_title_trgm ON catalog_products USING gin(title gin_trgm_ops);
CREATE INDEX idx_products_embedding ON catalog_products USING ivfflat(embedding vector_cosine_ops);

-- ================================================================
-- contributors
-- ================================================================

CREATE TABLE IF NOT EXISTS contributors (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  contributor_type_code CHAR(1) NOT NULL,
  contributor_role_code VARCHAR(10) NOT NULL,
  display_name VARCHAR(300) NOT NULL,
  given_name VARCHAR(200),
  family_name VARCHAR(200),
  title_of_honor VARCHAR(100),
  bio TEXT,
  sequence_number INT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ,
  CONSTRAINT chk_contributor_type CHECK (contributor_type_code IN ('P', 'C'))
);

CREATE INDEX idx_contributors_product_id ON contributors(product_id);
CREATE INDEX idx_contributors_role_code ON contributors(contributor_role_code);
CREATE INDEX idx_contributors_display_name ON contributors(display_name);

-- ================================================================
-- subjects
-- ================================================================

CREATE TABLE IF NOT EXISTS subjects (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  subject_scheme VARCHAR(10) NOT NULL,
  subject_code VARCHAR(50) NOT NULL,
  subject_text VARCHAR(500),
  is_primary BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_subjects_product_id ON subjects(product_id);
CREATE INDEX idx_subjects_scheme ON subjects(subject_scheme);
CREATE INDEX idx_subjects_code ON subjects(subject_code);

-- ================================================================
-- text_content
-- ================================================================

CREATE TABLE IF NOT EXISTS text_content (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  text_type_code VARCHAR(10) NOT NULL,
  language_code CHAR(3) DEFAULT 'ukr',
  text_content TEXT NOT NULL,
  sequence_number INT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_text_content_product_id ON text_content(product_id);
CREATE INDEX idx_text_content_type ON text_content(text_type_code);

-- ================================================================
-- media_files
-- ================================================================

CREATE TABLE IF NOT EXISTS media_files (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  media_file_type_code VARCHAR(10) NOT NULL,
  location_url VARCHAR(1024) NOT NULL,
  media_file_link_type_code VARCHAR(10),
  media_file_format_code VARCHAR(20),
  file_size_bytes BIGINT,
  display_text VARCHAR(500),
  download_capability BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_media_files_product_id ON media_files(product_id);
CREATE INDEX idx_media_files_type ON media_files(media_file_type_code);

-- ================================================================
-- prices (base table for partitioning)
-- ================================================================

CREATE TABLE IF NOT EXISTS prices (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  source_code VARCHAR(50) NOT NULL,
  currency_code CHAR(3) NOT NULL DEFAULT 'UAH',
  price_type_code VARCHAR(10) NOT NULL,
  price_amount DECIMAL(12,2) NOT NULL,
  price_date DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
) PARTITION BY RANGE (YEAR(price_date));

-- Create monthly partitions for 2024-2026
CREATE TABLE prices_2024_q1 PARTITION OF prices
  FOR VALUES FROM (2024) TO (2025);
CREATE TABLE prices_2025_q1 PARTITION OF prices
  FOR VALUES FROM (2025) TO (2026);
CREATE TABLE prices_2026_q1 PARTITION OF prices
  FOR VALUES FROM (2026) TO (2027);

CREATE INDEX idx_prices_product_id ON prices(product_id);
CREATE INDEX idx_prices_source ON prices(source_code);
CREATE INDEX idx_prices_date ON prices(price_date);

-- ================================================================
-- sales_rights
-- ================================================================

CREATE TABLE IF NOT EXISTS sales_rights (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  sales_rights_type_code VARCHAR(10) NOT NULL,
  territory VARCHAR(100),
  region_code CHAR(2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_sales_rights_product_id ON sales_rights(product_id);
CREATE INDEX idx_sales_rights_territory ON sales_rights(territory);

-- ================================================================
-- related_products
-- ================================================================

CREATE TABLE IF NOT EXISTS related_products (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  related_product_id BIGINT REFERENCES catalog_products(id) ON DELETE CASCADE,
  relation_code VARCHAR(10) NOT NULL,
  sequence_number INT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_related_products_product_id ON related_products(product_id);
CREATE INDEX idx_related_products_related_id ON related_products(related_product_id);

-- ================================================================
-- audit_log
-- ================================================================

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  table_name VARCHAR(100) NOT NULL,
  record_id BIGINT NOT NULL,
  operation VARCHAR(10) NOT NULL,
  old_values JSONB,
  new_values JSONB,
  changed_by VARCHAR(100),
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT chk_operation CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX idx_audit_log_table ON audit_log(table_name);
CREATE INDEX idx_audit_log_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_changed_at ON audit_log(changed_at DESC);

-- ================================================================
-- Auto-update triggers
-- ================================================================

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_catalog_products_timestamp
BEFORE UPDATE ON catalog_products
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_contributors_timestamp
BEFORE UPDATE ON contributors
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_subjects_timestamp
BEFORE UPDATE ON subjects
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_text_content_timestamp
BEFORE UPDATE ON text_content
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_media_files_timestamp
BEFORE UPDATE ON media_files
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_prices_timestamp
BEFORE UPDATE ON prices
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_sales_rights_timestamp
BEFORE UPDATE ON sales_rights
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_related_products_timestamp
BEFORE UPDATE ON related_products
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ================================================================
-- Materialized view for current prices (refreshed daily)
-- ================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS current_prices AS
SELECT DISTINCT ON (product_id, source_code)
  product_id,
  source_code,
  currency_code,
  price_type_code,
  price_amount,
  price_date,
  updated_at
FROM prices
WHERE deleted_at IS NULL
ORDER BY product_id, source_code, price_date DESC;

CREATE INDEX idx_current_prices_product ON current_prices(product_id);
CREATE INDEX idx_current_prices_source ON current_prices(source_code);
