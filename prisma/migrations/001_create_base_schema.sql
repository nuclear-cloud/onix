-- ================================================================
-- 001_create_base_schema.sql
-- Create all core tables with indexes
-- ================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- ================================================================
-- catalog_products
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

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_catalog_products_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_catalog_products_updated_at
  BEFORE UPDATE ON catalog_products
  FOR EACH ROW
  EXECUTE FUNCTION update_catalog_products_updated_at();

-- ================================================================
-- contributors
-- ================================================================

CREATE TABLE IF NOT EXISTS contributors (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  
  role_code VARCHAR(3) NOT NULL,
  sequence_number INT,
  
  contributor_type CHAR(1) NOT NULL,
  person_name VARCHAR(300),
  person_name_inverted VARCHAR(300),
  key_names VARCHAR(200),
  names_before_key VARCHAR(200),
  corporate_name VARCHAR(300),
  
  biographical_note TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  CONSTRAINT chk_contributor_name CHECK (
    (contributor_type = 'P' AND person_name IS NOT NULL) OR
    (contributor_type = 'C' AND corporate_name IS NOT NULL)
  )
);

CREATE INDEX idx_contributors_product ON contributors(product_id);
CREATE INDEX idx_contributors_role ON contributors(role_code);
CREATE INDEX idx_contributors_name ON contributors(person_name);
CREATE INDEX idx_contributors_name_trgm ON contributors USING gin(person_name gin_trgm_ops);

-- ================================================================
-- subjects
-- ================================================================

CREATE TABLE IF NOT EXISTS subjects (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  
  scheme_code VARCHAR(10) NOT NULL,
  subject_code VARCHAR(100),
  subject_heading_text VARCHAR(500) NOT NULL,
  
  is_primary BOOLEAN DEFAULT false,
  sequence_number INT
);

CREATE INDEX idx_subjects_product ON subjects(product_id);
CREATE INDEX idx_subjects_scheme ON subjects(scheme_code);
CREATE INDEX idx_subjects_code ON subjects(subject_code);
CREATE INDEX idx_subjects_primary ON subjects(product_id, is_primary) WHERE is_primary = true;

-- ================================================================
-- text_content
-- ================================================================

CREATE TABLE IF NOT EXISTS text_content (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  
  text_type_code CHAR(2) NOT NULL,
  content TEXT NOT NULL,
  author VARCHAR(200),
  source_title VARCHAR(300),
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_text_content_product ON text_content(product_id);
CREATE INDEX idx_text_content_type ON text_content(text_type_code);

-- ================================================================
-- media_files
-- ================================================================

CREATE TABLE IF NOT EXISTS media_files (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  
  resource_content_type_code CHAR(2) NOT NULL,
  resource_mode_code CHAR(2) NOT NULL,
  
  file_format_code CHAR(2),
  file_link_type CHAR(2),
  file_link TEXT NOT NULL,
  
  width_px INT,
  height_px INT,
  file_size_bytes BIGINT,
  
  sequence_number INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_media_product ON media_files(product_id);
CREATE INDEX idx_media_type ON media_files(resource_content_type_code);

-- ================================================================
-- price_sources
-- ================================================================

CREATE TABLE IF NOT EXISTS price_sources (
  id SERIAL PRIMARY KEY,
  source_code VARCHAR(50) UNIQUE NOT NULL,
  source_name VARCHAR(200) NOT NULL,
  source_type VARCHAR(20) NOT NULL,
  api_endpoint VARCHAR(500),
  is_active BOOLEAN DEFAULT true,
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_price_sources_active ON price_sources(is_active);

-- ================================================================
-- prices (partitioned by month)
-- ================================================================

CREATE TABLE IF NOT EXISTS prices (
  id BIGSERIAL,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  source_id INT NOT NULL REFERENCES price_sources(id),
  
  price_type_code CHAR(2) NOT NULL,
  price_amount DECIMAL(12,2) NOT NULL,
  currency_code CHAR(3) NOT NULL DEFAULT 'UAH',
  
  tax_type_code CHAR(2),
  tax_rate_percent DECIMAL(5,2),
  tax_amount DECIMAL(12,2),
  
  price_effective_from DATE,
  price_effective_until DATE,
  
  discount_percent DECIMAL(5,2),
  stock_quantity INT,
  
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  
  PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

-- Create partitions for current year (auto-create via function)
CREATE TABLE prices_2025_01 PARTITION OF prices
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE prices_2025_02 PARTITION OF prices
  FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE prices_2025_03 PARTITION OF prices
  FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE prices_2025_04 PARTITION OF prices
  FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE prices_2025_05 PARTITION OF prices
  FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE prices_2025_06 PARTITION OF prices
  FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE prices_2025_07 PARTITION OF prices
  FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE prices_2025_08 PARTITION OF prices
  FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE prices_2025_09 PARTITION OF prices
  FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE prices_2025_10 PARTITION OF prices
  FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE prices_2025_11 PARTITION OF prices
  FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE prices_2025_12 PARTITION OF prices
  FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE INDEX idx_prices_product ON prices(product_id, recorded_at DESC);
CREATE INDEX idx_prices_source ON prices(source_id, recorded_at DESC);
CREATE INDEX idx_prices_current ON prices(product_id, source_id, recorded_at DESC);

-- ================================================================
-- sales_rights
-- ================================================================

CREATE TABLE IF NOT EXISTS sales_rights (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  
  sales_rights_type_code CHAR(2) NOT NULL,
  territory_countries VARCHAR(10)[],
  territory_regions VARCHAR(10)[],
  
  start_date DATE,
  end_date DATE
);

CREATE INDEX idx_sales_rights_product ON sales_rights(product_id);
CREATE INDEX idx_sales_rights_countries ON sales_rights USING GIN(territory_countries);

-- ================================================================
-- related_products
-- ================================================================

CREATE TABLE IF NOT EXISTS related_products (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  related_product_id BIGINT NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
  
  relation_code CHAR(2) NOT NULL,
  
  UNIQUE(product_id, related_product_id),
  CONSTRAINT chk_no_self_relation CHECK (product_id != related_product_id)
);

CREATE INDEX idx_related_from ON related_products(product_id);
CREATE INDEX idx_related_to ON related_products(related_product_id);

-- ================================================================
-- audit_log
-- ================================================================

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  table_name VARCHAR(50) NOT NULL,
  record_id BIGINT NOT NULL,
  operation VARCHAR(10) NOT NULL,
  old_data JSONB,
  new_data JSONB,
  changed_by VARCHAR(100),
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_time ON audit_log(changed_at);

-- ================================================================
-- Materialized View: current_prices
-- Refresh every 6 hours via cron or app scheduler
-- ================================================================

DROP MATERIALIZED VIEW IF EXISTS current_prices;

CREATE MATERIALIZED VIEW current_prices AS
SELECT DISTINCT ON (product_id, source_id)
  product_id,
  source_id,
  price_type_code,
  price_amount,
  currency_code,
  tax_rate_percent,
  stock_quantity,
  recorded_at
FROM prices
WHERE recorded_at >= NOW() - INTERVAL '7 days'
ORDER BY product_id, source_id, recorded_at DESC;

CREATE UNIQUE INDEX idx_current_prices_unique ON current_prices(product_id, source_id);
CREATE INDEX idx_current_prices_amount ON current_prices(price_amount);
