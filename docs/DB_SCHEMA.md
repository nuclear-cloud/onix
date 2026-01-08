# Database Schema Documentation

**Architecture Version:** V3.0 (Strict ONIX Compliance)
**Date:** 2026-01-05

The database is split into two distinct domains:
1.  **Catalog (`catalog_`)**: "Golden Records" - fully normalized ONIX 3.0 structure.
2.  **Market (`offers`, `suppliers`)**: High-frequency price & stock data.

**Reference Standards:**
*   **ONIX 3.0 Code Lists (Issue 71)**: Stored in `data/ONIX_BookProduct_Codelists_Issue_71.xml`.
*   **Thema Classification (v1.6 UK)**: Stored in `data/thema_v1.6_uk.json` and loaded into `ref_thema_subjects`.

## 📊 Visual Schema (dbdiagram.io)

Copy the code below and paste it into [dbdiagram.io](https://dbdiagram.io/d).

```dbml
// ONIX Aggregator Database Schema V3.0
// Render at: https://dbdiagram.io/

Project ONIX_Aggregator {
  database_type: 'PostgreSQL'
  Note: 'Strict ONIX 3.0 Normalization'
}

// ==========================================
// REFERENCES (Dictionaries)
// ==========================================

Table ref_thema_subjects {
  code varchar(6) [pk]
  parent_code varchar(6)
  label_en varchar(255)
  label_uk varchar(255)
  description_uk text
  
  Note: 'Loaded from Thema v1.6 JSON'
}

// ==========================================
// CATALOG DOMAIN (Static Metadata)
// ==========================================

Table catalog_products {
  id uuid [pk]
  record_reference varchar(100) [unique, note: 'Internal ID or ISBN']
  notification_type varchar
  isbn_13 varchar(13) [unique]
  ean varchar(13) [unique]
  sku varchar(50)
  
  product_form varchar [note: 'BB=Hard, BC=Soft']
  product_form_detail varchar
  edition_number integer
  
  publishing_status varchar
  is_ukrainian boolean
  
  onix_full jsonb [note: 'Fallback for extra fields']
  
  publisher_id uuid
  created_at timestamp
  updated_at timestamp
}

Table catalog_publishers {
  id uuid [pk]
  name varchar(255) [unique]
  gln varchar(13)
}

Table catalog_contributors {
  id uuid [pk]
  name varchar(255)
  person_name_inverted varchar(255)
  biographical_note text
}

Table catalog_product_contributors_link {
  product_id uuid [pk]
  contributor_id uuid [pk]
  role varchar [pk, note: 'A01=Author, B06=Translator']
  sequence_number integer
}

Table catalog_collections {
  id uuid [pk]
  title varchar(1000)
  type varchar [note: '10=Publisher Series']
  issn varchar(8)
}

Table catalog_product_collections_link {
  product_id uuid [pk]
  collection_id uuid [pk]
  sequence_type varchar [default: '02']
  sequence_number varchar [note: 'Vol. 1']
}

// --- CATALOG SUB-TABLES ---

Table catalog_titles {
  id uuid [pk]
  product_id uuid
  type varchar [note: '01=Distinctive']
  title_text text
  subtitle text
}

Table catalog_languages {
  id uuid [pk]
  product_id uuid
  role varchar [note: '01=Text']
  code varchar(3) [note: 'ukr, eng']
}

Table catalog_subjects {
  id uuid [pk]
  product_id uuid
  scheme_identifier varchar [note: '10=BISAC, 20=Keywords, 93=Thema']
  subject_code varchar
  subject_heading_text varchar
  
  Note: 'If scheme=93, links to ref_thema_subjects'
}

Table catalog_extents {
    id uuid [pk]
    product_id uuid
    type varchar [note: '00=Pages, 05=Duration']
    value decimal
    unit varchar [note: 'Pages, Hours']
}

Table catalog_measures {
    id uuid [pk]
    product_id uuid
    type varchar [note: '01=Height, 02=Width']
    measurement decimal
    unit_code varchar [note: 'mm, gr']
}

Table catalog_audience_ranges {
    id uuid [pk]
    product_id uuid
    qualifier varchar [note: '11=Age']
    precision varchar [note: '03=From']
    value varchar
}

Table catalog_prizes {
    id uuid [pk]
    product_id uuid
    name varchar
    year varchar
    country varchar
    code varchar [note: '02=Winner']
}

Table catalog_text_contents {
    id uuid [pk]
    product_id uuid
    type varchar [note: '03=Description']
    text text
    author varchar
}

Table catalog_cited_contents {
    id uuid [pk]
    product_id uuid
    type varchar [note: '06=Review']
    source_title varchar
    citation_note text
    link varchar
}

Table catalog_related_products {
    id uuid [pk]
    product_id uuid
    relation_code varchar [note: '06=Alt Format']
    related_product_id_type varchar
    related_product_id_value varchar
}

Table catalog_publishing_dates {
    id uuid [pk]
    product_id uuid
    role varchar [note: '01=Pub Date']
    date_value varchar
    date_format varchar
}

// ==========================================
// MARKET DOMAIN (Dynamic Prices)
// ==========================================

Table suppliers {
  id uuid [pk]
  name varchar(255) [unique]
  code varchar(50) [unique]
  base_url varchar
  is_active boolean
}

Table offers {
  id uuid [pk]
  book_id uuid
  supplier_id uuid
  sku varchar(100)
  url text
  price decimal(10,2)
  price_old decimal(10,2)
  currency varchar(3)
  availability varchar
  in_stock boolean
  last_updated timestamp
  
  indexes {
    (book_id, supplier_id) [unique]
  }
}

Table price_history {
  id uuid [pk]
  offer_id uuid
  price decimal(10,2)
  currency varchar(3)
  availability varchar
  recorded_at timestamp [pk, note: 'Partition Key']
}

// ==========================================
// RELATIONS
// ==========================================

// References
Ref: ref_thema_subjects.parent_code > ref_thema_subjects.code

// Catalog Internal
Ref: catalog_products.publisher_id > catalog_publishers.id

Ref: catalog_product_contributors_link.product_id > catalog_products.id [delete: cascade]
Ref: catalog_product_contributors_link.contributor_id > catalog_contributors.id [delete: cascade]

Ref: catalog_product_collections_link.product_id > catalog_products.id [delete: cascade]
Ref: catalog_product_collections_link.collection_id > catalog_collections.id [delete: cascade]

Ref: catalog_titles.product_id > catalog_products.id [delete: cascade]
Ref: catalog_languages.product_id > catalog_products.id [delete: cascade]
Ref: catalog_subjects.product_id > catalog_products.id [delete: cascade]
Ref: catalog_extents.product_id > catalog_products.id [delete: cascade]
Ref: catalog_measures.product_id > catalog_products.id [delete: cascade]
Ref: catalog_audience_ranges.product_id > catalog_products.id [delete: cascade]
Ref: catalog_prizes.product_id > catalog_products.id [delete: cascade]
Ref: catalog_text_contents.product_id > catalog_products.id [delete: cascade]
Ref: catalog_cited_contents.product_id > catalog_products.id [delete: cascade]
Ref: catalog_related_products.product_id > catalog_products.id [delete: cascade]
Ref: catalog_publishing_dates.product_id > catalog_products.id [delete: cascade]

// Market Internal
Ref: offers.supplier_id > suppliers.id
Ref: price_history.offer_id > offers.id [delete: cascade]

// Cross-Domain
Ref: offers.book_id > catalog_products.id
```
