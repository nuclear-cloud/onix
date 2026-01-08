-- Migration: Composite PKs, soft delete flags, and indexes for reference tables
-- Date: 2026-01-06
-- Note: Run in a maintenance window. This script is idempotent and safe to re-run.

BEGIN;

-- 1) ref_onix_codelists: move to composite PK (list_number, code), add is_active
ALTER TABLE ref_onix_codelists
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Drop old PK on id (if present) and remove id column
ALTER TABLE ref_onix_codelists DROP CONSTRAINT IF EXISTS ref_onix_codelists_pkey;
ALTER TABLE ref_onix_codelists DROP CONSTRAINT IF EXISTS uq_ref_onix_list_code;
ALTER TABLE ref_onix_codelists DROP COLUMN IF EXISTS id;

-- Add composite primary key
ALTER TABLE ref_onix_codelists
    ADD CONSTRAINT pk_ref_onix_codelists PRIMARY KEY (list_number, code);

-- Ensure list_number index exists (for filtering)
CREATE INDEX IF NOT EXISTS ix_ref_onix_codelists_list_number
    ON ref_onix_codelists(list_number);

-- 2) ref_thema_subjects: add is_active, label index for UI sorting
ALTER TABLE ref_thema_subjects
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS ix_ref_thema_label_uk
    ON ref_thema_subjects(label_uk);

COMMIT;
