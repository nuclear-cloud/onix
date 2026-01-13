-- Enable schemas
CREATE SCHEMA IF NOT EXISTS cold;
CREATE SCHEMA IF NOT EXISTS fact;

-- Enum for cold.RawIngestion
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'rawingestionstatus' AND n.nspname = 'cold'
    ) THEN
        CREATE TYPE cold."RawIngestionStatus" AS ENUM ('PENDING', 'PROCESSED', 'FAILED');
    END IF;
END $$;

-- Table cold.rawingestion
CREATE TABLE IF NOT EXISTS cold."RawIngestion" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    fingerprint VARCHAR(128) NOT NULL UNIQUE,
    status cold."RawIngestionStatus" NOT NULL DEFAULT 'PENDING',
    error TEXT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_rawingestion_provider_status_ingested_at
    ON cold."RawIngestion" (provider, status, ingested_at);

-- Fact tables
CREATE TABLE IF NOT EXISTS fact."Fact_Identifier" (
    id BIGSERIAL PRIMARY KEY,
    product_ref VARCHAR(64) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    confidence INT NOT NULL DEFAULT 50,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    raw_value JSONB NULL,
    id_type VARCHAR(10) NOT NULL,
    value VARCHAR(100) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fact_identifier_product_ref
    ON fact."Fact_Identifier" (product_ref);
CREATE INDEX IF NOT EXISTS idx_fact_identifier_provider_observed
    ON fact."Fact_Identifier" (provider_id, observed_at);

CREATE TABLE IF NOT EXISTS fact."Fact_Title" (
    id BIGSERIAL PRIMARY KEY,
    product_ref VARCHAR(64) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    confidence INT NOT NULL DEFAULT 50,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    raw_value JSONB NULL,
    title TEXT NOT NULL,
    subtitle TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_fact_title_product_ref
    ON fact."Fact_Title" (product_ref);
CREATE INDEX IF NOT EXISTS idx_fact_title_provider_observed
    ON fact."Fact_Title" (provider_id, observed_at);

CREATE TABLE IF NOT EXISTS fact."Fact_Contributor" (
    id BIGSERIAL PRIMARY KEY,
    product_ref VARCHAR(64) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    confidence INT NOT NULL DEFAULT 50,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    raw_value JSONB NULL,
    raw_name TEXT NOT NULL,
    role_code VARCHAR(3) NOT NULL,
    sequence_number INT NULL
);
CREATE INDEX IF NOT EXISTS idx_fact_contributor_product_ref
    ON fact."Fact_Contributor" (product_ref);
CREATE INDEX IF NOT EXISTS idx_fact_contributor_provider_observed
    ON fact."Fact_Contributor" (provider_id, observed_at);

CREATE TABLE IF NOT EXISTS fact."Fact_Subject" (
    id BIGSERIAL PRIMARY KEY,
    product_ref VARCHAR(64) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    confidence INT NOT NULL DEFAULT 50,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    raw_value JSONB NULL,
    scheme_code VARCHAR(10) NOT NULL,
    subject_code VARCHAR(100) NULL,
    subject_heading_text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fact_subject_product_ref
    ON fact."Fact_Subject" (product_ref);
CREATE INDEX IF NOT EXISTS idx_fact_subject_provider_observed
    ON fact."Fact_Subject" (provider_id, observed_at);

CREATE TABLE IF NOT EXISTS fact."Fact_Price" (
    id BIGSERIAL PRIMARY KEY,
    product_ref VARCHAR(64) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    confidence INT NOT NULL DEFAULT 50,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    raw_value JSONB NULL,
    currency_code CHAR(3) NOT NULL,
    price_amount DECIMAL(12,2) NOT NULL,
    price_type_code CHAR(2) NOT NULL,
    availability VARCHAR(50) NULL,
    stock_quantity INT NULL
);
CREATE INDEX IF NOT EXISTS idx_fact_price_product_ref
    ON fact."Fact_Price" (product_ref);
CREATE INDEX IF NOT EXISTS idx_fact_price_provider_observed
    ON fact."Fact_Price" (provider_id, observed_at);

CREATE TABLE IF NOT EXISTS fact."Fact_Media" (
    id BIGSERIAL PRIMARY KEY,
    product_ref VARCHAR(64) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    confidence INT NOT NULL DEFAULT 50,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    raw_value JSONB NULL,
    resource_content_type_code CHAR(2) NOT NULL,
    resource_mode_code CHAR(2) NOT NULL,
    file_link TEXT NOT NULL,
    width_px INT NULL,
    height_px INT NULL
);
CREATE INDEX IF NOT EXISTS idx_fact_media_product_ref
    ON fact."Fact_Media" (product_ref);
CREATE INDEX IF NOT EXISTS idx_fact_media_provider_observed
    ON fact."Fact_Media" (provider_id, observed_at);
