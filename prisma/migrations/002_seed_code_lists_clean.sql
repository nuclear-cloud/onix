-- ================================================================
-- 002_seed_code_lists.sql
-- Seed ONIX 3.0 reference code lists
-- ================================================================

-- ================================================================
-- ProductForm codes (ONIX List 150)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_product_form (
  code CHAR(2) PRIMARY KEY,
  description VARCHAR(200) NOT NULL,
  category VARCHAR(50)
);

TRUNCATE TABLE code_list_product_form;

INSERT INTO code_list_product_form (code, description, category) VALUES
  ('BA', 'Hardback', 'Print'),
  ('BB', 'Paperback / softback', 'Print'),
  ('BC', 'Saddle-stitched', 'Print'),
  ('BD', 'Cloth over boards', 'Print'),
  ('BE', 'Cloth boards, dust jacket', 'Print'),
  ('BF', 'Cloth boards, no dust jacket', 'Print'),
  ('BG', 'Paperback, dust jacket', 'Print'),
  ('BH', 'Hardback, dust jacket', 'Print'),
  ('BJ', 'Saddle-sewn', 'Print'),
  ('BK', 'Hardback, no dust jacket', 'Print'),
  ('BL', 'Paperback, no dust jacket', 'Print'),
  ('EA', 'PDF', 'Digital'),
  ('EB', 'EPUB', 'Digital'),
  ('EC', 'EPUB3', 'Digital'),
  ('ED', 'HTML', 'Digital'),
  ('EE', 'Microsoft Word', 'Digital'),
  ('EF', 'OpenDocument text', 'Digital'),
  ('FA', 'Unspecified audio format', 'Audio'),
  ('FB', 'Audio cassette', 'Audio'),
  ('FC', 'CD audio', 'Audio');

-- ================================================================
-- Publishing Status codes (ONIX List 64)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_publishing_status (
  code CHAR(2) PRIMARY KEY,
  description VARCHAR(200) NOT NULL
);

TRUNCATE TABLE code_list_publishing_status;

INSERT INTO code_list_publishing_status (code, description) VALUES
  ('00', 'Unspecified'),
  ('01', 'Active'),
  ('02', 'Out of Print'),
  ('03', 'Reprint'),
  ('04', 'Not yet published'),
  ('05', 'Cancelled'),
  ('06', 'Forthcoming'),
  ('07', 'Withdrawn'),
  ('08', 'In preparation'),
  ('09', 'Pre-order');

-- ================================================================
-- Contributor Role codes (ONIX List 17)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_contributor_role (
  code VARCHAR(10) PRIMARY KEY,
  description VARCHAR(300) NOT NULL
);

TRUNCATE TABLE code_list_contributor_role;

INSERT INTO code_list_contributor_role (code, description) VALUES
  ('A01', 'By-line author'),
  ('A02', 'With'),
  ('A03', 'Screenplay by'),
  ('A04', 'Libretto by'),
  ('A05', 'Lyrics by'),
  ('A06', 'Composed by'),
  ('A07', 'Director'),
  ('A08', 'Producer'),
  ('A09', 'Conductor'),
  ('A10', 'Performed by'),
  ('B01', 'Editor'),
  ('B02', 'Co-editor'),
  ('B03', 'Associate editor'),
  ('B04', 'Translation by'),
  ('B05', 'Annotated by'),
  ('B06', 'Introduction by'),
  ('B07', 'Foreword by');

-- ================================================================
-- Price Type codes (ONIX List 58)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_price_type (
  code VARCHAR(10) PRIMARY KEY,
  description VARCHAR(200) NOT NULL
);

TRUNCATE TABLE code_list_price_type;

INSERT INTO code_list_price_type (code, description) VALUES
  ('01', 'RRP - Recommended Retail Price'),
  ('02', 'Fixed retail price'),
  ('05', 'Wholesale discount'),
  ('08', 'Agent net price'),
  ('09', 'SRP - Suggested Retail Price'),
  ('11', 'Net price (recommended)'),
  ('12', 'Net price (contractual)'),
  ('13', 'Net price (promotional)'),
  ('14', 'Net price (educational)');

-- ================================================================
-- Text Type codes (ONIX List 27)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_text_type (
  code VARCHAR(10) PRIMARY KEY,
  description VARCHAR(200) NOT NULL
);

TRUNCATE TABLE code_list_text_type;

INSERT INTO code_list_text_type (code, description) VALUES
  ('01', 'Frontmatter - cover copy'),
  ('02', 'Frontmatter - publisher description'),
  ('03', 'Frontmatter - table of contents'),
  ('04', 'Frontmatter - author biography'),
  ('05', 'Frontmatter - subject'),
  ('06', 'Description'),
  ('07', 'Note'),
  ('08', 'Review quote'),
  ('09', 'Review - source'),
  ('10', 'Review - author'),
  ('11', 'Review - text of review'),
  ('12', 'Primary'),
  ('13', 'Collection'),
  ('14', 'Extracted'),
  ('15', 'Author statement'),
  ('16', 'Other editorial comment'),
  ('17', 'Promotional headline'),
  ('18', 'Previous review text'),
  ('19', 'Endorsement'),
  ('20', 'Resource file URL'),
  ('21', 'Teaser text for book');

-- ================================================================
-- Audience codes (ONIX List 28)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_audience (
  code CHAR(2) PRIMARY KEY,
  description VARCHAR(200) NOT NULL
);

TRUNCATE TABLE code_list_audience;

INSERT INTO code_list_audience (code, description) VALUES
  ('00', 'Unspecified'),
  ('01', 'Juvenile'),
  ('02', 'Young adult'),
  ('03', 'Adult'),
  ('04', 'Academic/professional'),
  ('05', 'Educational/reference'),
  ('06', 'University/higher education'),
  ('07', 'Professional/trade');

-- ================================================================
-- Subject Scheme codes
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_subject_scheme (
  code VARCHAR(20) PRIMARY KEY,
  description VARCHAR(200) NOT NULL,
  url VARCHAR(500)
);

TRUNCATE TABLE code_list_subject_scheme;

INSERT INTO code_list_subject_scheme (code, description, url) VALUES
  ('BISAC', 'BISAC Subject Headings', 'https://www.bisg.org/bisac'),
  ('BIC', 'BIC Standard Subject Qualifiers', 'https://www.bic.org.uk/'),
  ('THEMA', 'Thema Subject Category', 'https://www.editeur.org/151/Thema/'),
  ('UDC', 'Universal Decimal Classification', 'https://www.udc.org/'),
  ('BBK', 'Bibliotečna Bibliotečna Klasifikacija (Russian)', 'https://www.rsl.ru/'),
  ('DK-018', 'Danish Standards (DK-018)', 'https://www.ds.dk/'),
  ('LCSH', 'Library of Congress Subject Headings', 'https://www.loc.gov/'),
  ('UKRCAT', 'Ukrainian National Bibliography', 'https://litmistetstvo.org/');

-- ================================================================
-- Verify new schema
-- ================================================================

SELECT 
  'catalog_products' as table_name, count(*) as record_count 
FROM catalog_products
UNION ALL
SELECT 'contributors', count(*) FROM contributors
UNION ALL
SELECT 'subjects', count(*) FROM subjects
UNION ALL
SELECT 'text_content', count(*) FROM text_content
UNION ALL
SELECT 'media_files', count(*) FROM media_files
UNION ALL
SELECT 'prices', count(*) FROM prices
UNION ALL
SELECT 'sales_rights', count(*) FROM sales_rights
UNION ALL
SELECT 'related_products', count(*) FROM related_products;
