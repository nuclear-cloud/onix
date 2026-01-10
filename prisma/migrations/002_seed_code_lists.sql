-- ================================================================
-- 002_seed_code_lists.sql
-- Seed ONIX 3.0 code lists
-- ================================================================

-- ================================================================
-- ProductForm codes (ONIX List 150)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_product_form (
  code CHAR(2) PRIMARY KEY,
  description VARCHAR(200) NOT NULL,
  category VARCHAR(50)
);

TRUNCATE code_list_product_form;

INSERT INTO code_list_product_form (code, description, category) VALUES
  -- Print books
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
  
  -- eBooks
  ('EA', 'PDF', 'Digital'),
  ('EB', 'EPUB', 'Digital'),
  ('EC', 'EPUB3', 'Digital'),
  ('ED', 'HTML', 'Digital'),
  ('EE', 'Microsoft Word', 'Digital'),
  ('EF', 'OpenDocument text', 'Digital'),
  
  -- Audio
  ('FA', 'Unspecified audio format', 'Audio'),
  ('FB', 'Audio cassette', 'Audio'),
  ('FC', 'CD audio', 'Audio'),
  ('FD', 'DAT audio cassette', 'Audio'),
  ('FE', 'Digital audio', 'Audio'),
  ('FF', 'Mini-disc audio', 'Audio'),
  ('FG', 'VinylLP audio', 'Audio'),
  ('FH', 'Downloaded audio file', 'Audio'),
  ('FI', 'Audiobook (downloadable)', 'Audio'),
  ('FJ', 'Digital audio player (device with content)', 'Audio');

-- ================================================================
-- PublishingStatus codes (ONIX List 64)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_publishing_status (
  code CHAR(2) PRIMARY KEY,
  description VARCHAR(200) NOT NULL
);

TRUNCATE code_list_publishing_status;

INSERT INTO code_list_publishing_status (code, description) VALUES
  ('00', 'Unspecified'),
  ('01', 'Active'),
  ('02', 'Out of print'),
  ('03', 'Reprint'),
  ('04', 'Not yet published'),
  ('05', 'Cancelled'),
  ('06', 'Recalled'),
  ('07', 'Superseded'),
  ('08', 'Withdrawn'),
  ('09', 'Active; new edition in progress');

-- ================================================================
-- ContributorRole codes (ONIX List 17)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_contributor_role (
  code VARCHAR(3) PRIMARY KEY,
  description VARCHAR(200) NOT NULL,
  category VARCHAR(50)
);

TRUNCATE code_list_contributor_role;

INSERT INTO code_list_contributor_role (code, description, category) VALUES
  -- Author roles
  ('A01', 'By-line author', 'Author'),
  ('A02', 'With author', 'Author'),
  ('A03', 'Screenplay by', 'Author'),
  ('A04', 'Librettist', 'Author'),
  ('A05', 'Lyricist', 'Author'),
  ('A06', 'Composer', 'Author'),
  
  -- Illustrator roles
  ('A14', 'Illustrator', 'Illustrator'),
  ('A15', 'Cartographer', 'Illustrator'),
  ('A17', 'Photographer', 'Illustrator'),
  
  -- Translator roles
  ('B06', 'Translator', 'Translator'),
  ('B07', 'Translator (from)', 'Translator'),
  ('B08', 'Translator (to)', 'Translator'),
  
  -- Editor roles
  ('B01', 'Editor', 'Editor'),
  ('B02', 'Editor-in-chief', 'Editor'),
  ('B03', 'Guest editor', 'Editor'),
  
  -- Publisher roles
  ('B21', 'Publisher', 'Publisher'),
  
  -- Other
  ('A99', 'Other contributor', 'Other');

-- ================================================================
-- PriceType codes (ONIX List 58)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_price_type (
  code CHAR(2) PRIMARY KEY,
  description VARCHAR(200) NOT NULL
);

TRUNCATE code_list_price_type;

INSERT INTO code_list_price_type (code, description) VALUES
  ('01', 'RRP (Recommended Retail Price) excluding tax'),
  ('02', 'Agency price excluding tax'),
  ('03', 'Wholesale price (net) excluding tax'),
  ('04', 'Wholesale price (net) including tax'),
  ('05', 'RRP (Recommended Retail Price) including tax'),
  ('06', 'Agency price including tax'),
  ('41', 'Promotional price'),
  ('42', 'Member exclusive price'),
  ('43', 'Library price');

-- ================================================================
-- TextType codes (ONIX List 45)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_text_type (
  code CHAR(2) PRIMARY KEY,
  description VARCHAR(200) NOT NULL
);

TRUNCATE code_list_text_type;

INSERT INTO code_list_text_type (code, description) VALUES
  ('01', 'Main description'),
  ('02', 'Short description'),
  ('03', 'Long description'),
  ('04', 'Table of contents'),
  ('05', 'First chapter or sample text'),
  ('08', 'Full text of item'),
  ('09', 'Promoted content'),
  ('10', 'Back cover text'),
  ('11', 'Flap text'),
  ('12', 'Review'),
  ('13', 'Endorsement'),
  ('14', 'Author biography'),
  ('23', 'Excerpt'),
  ('24', 'Foreword'),
  ('25', 'Preface'),
  ('30', 'Publisher review'),
  ('31', 'Review quote'),
  ('32', 'Review source'),
  ('40', 'Announcement'),
  ('41', 'New product announcement');

-- ================================================================
-- Audience codes (ONIX List 28)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_audience (
  code CHAR(2) PRIMARY KEY,
  description VARCHAR(200) NOT NULL
);

TRUNCATE code_list_audience;

INSERT INTO code_list_audience (code, description) VALUES
  ('01', 'General / trade'),
  ('02', 'Children / juvenile'),
  ('03', 'Young adult'),
  ('04', 'Professional and scholarly'),
  ('05', 'Academic'),
  ('06', 'General adult'),
  ('07', 'Hardcover fiction'),
  ('08', 'Paperback fiction');

-- ================================================================
-- SubjectScheme codes (ONIX List 27)
-- ================================================================

CREATE TABLE IF NOT EXISTS code_list_subject_scheme (
  code VARCHAR(10) PRIMARY KEY,
  description VARCHAR(200) NOT NULL,
  url VARCHAR(500)
);

TRUNCATE code_list_subject_scheme;

INSERT INTO code_list_subject_scheme (code, description, url) VALUES
  ('BISAC', 'BISAC Subject Headings', 'https://www.bisg.org/bisac'),
  ('BIC', 'BIC Subject Categories', 'https://www.bic.org.uk/'),
  ('Thema', 'Thema subject scheme', 'https://www.thema.info/'),
  ('UDC', 'Universal Decimal Classification', 'https://www.udcc.org/'),
  ('BBK', 'Bibliotechno-bibliograficheskaya Klassifikaciya (Russian)', 'https://www.arbicon.ru/'),
  ('DK18', 'Derzhavnyy Klasyfikator Ukrayiny', 'https://www.sc.gov.ua/'),
  ('keywords', 'Keywords / free text', NULL),
  ('LCSH', 'Library of Congress Subject Headings', 'https://www.loc.gov/subjects/');

-- ================================================================
-- Function: auto-create monthly price partitions
-- ================================================================

CREATE OR REPLACE FUNCTION create_price_partition()
RETURNS void AS $$
DECLARE
  next_month DATE;
  partition_name TEXT;
  start_date DATE;
  end_date DATE;
BEGIN
  next_month := DATE_TRUNC('month', NOW()) + INTERVAL '1 month';
  partition_name := 'prices_' || TO_CHAR(next_month, 'YYYY_MM');
  start_date := DATE_TRUNC('month', next_month)::DATE;
  end_date := (DATE_TRUNC('month', next_month) + INTERVAL '1 month')::DATE;
  
  -- Check if partition already exists
  IF NOT EXISTS (
    SELECT 1 FROM pg_tables 
    WHERE tablename = partition_name
  ) THEN
    EXECUTE 'CREATE TABLE ' || partition_name || ' PARTITION OF prices
      FOR VALUES FROM (''' || start_date || ''') TO (''' || end_date || ''')';
    RAISE NOTICE 'Created partition: %', partition_name;
  END IF;
END;
$$ LANGUAGE plpgsql;

-- Create partitions for 2026
SELECT create_price_partition();
