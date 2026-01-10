# Yakaboo JSON → Database Mapping Reference

Complete field mapping documentation showing how raw Yakaboo JSON transforms into PostgreSQL database records.

**Data Flow**: `Yakaboo JSON` → `YakabooDataAdapter` → `ProductDTO` → `Prisma` → `PostgreSQL`

---

## � Quick Reference (Simple Table)

| Yakaboo JSON | → | DB Table.Column |
|--------------|---|-----------------|
| `barcode` | → | `catalog_products.isbn13` |
| `name` | → | `catalog_products.title` |
| `book_lang[0]` | → | `catalog_products.language_code` |
| `book_publisher_label[0].label` | → | `catalog_products.publisher_name` |
| `book_page_count` | → | `catalog_products.page_count` |
| `book_binding_type_label[0].label` | → | `catalog_products.product_form_code` |
| `status` | → | `catalog_products.publishing_status_code` |
| `author_label[].label` | → | `Contributor.person_name` |
| `book_translator_label[].label` | → | `Contributor.person_name` (role=B06) |
| `category_ids[]` | → | `Subject.subject_code` |
| `keywords` | → | `Subject.subject_heading_text` |
| `description` | → | `TextContent.content` |
| `image` | → | `MediaFile.file_link` |
| `mediagallery_image[]` | → | `MediaFile.file_link` |
| `price` | → | `Price.price_amount` |
| `original_price` | → | `Price.discount_percent` (calculated) |

---

## �📍 Quick Navigation

- [Main Product Fields](#1-main-product-fields-catalogproduct)
- [Contributors (Authors)](#2-contributors-authors-translators)
- [Subjects (Categories/Keywords)](#3-subjects-categorieskeywords)
- [Text Content (Descriptions)](#4-text-content-descriptions)
- [Media Files (Images)](#5-media-files-images)
- [Prices](#6-prices)
- [Language Code Mapping](#7-language-code-mapping)
- [Product Form (Binding) Mapping](#8-product-form-binding-mapping)
- [Status Mapping](#9-publishing-status-mapping)
- [Metadata Storage](#10-metadata-json-field)

---

## 1. Main Product Fields (`CatalogProduct`)

| Yakaboo JSON Field | ProductDTO Field | DB Column | DB Type | Notes |
|-------------------|------------------|-----------|---------|-------|
| `barcode` / `book_isbn` / `book_isbn_label[0].label` | `isbn13` | `isbn13` | `VARCHAR(13)` | Normalized: removes dashes/spaces, validates 13-digit |
| `sku` | `proprietary_id` | `proprietary_id` | `VARCHAR(100)` | Yakaboo internal SKU |
| `name` | `title` | `title` | `VARCHAR(500)` | Default: "Без назви" if empty |
| `short_description` | `subtitle` | `subtitle` | `VARCHAR(500)` | First 500 chars |
| `book_binding_type_label[0].label` | `product_form_code` | `product_form_code` | `CHAR(2)` | Mapped via BINDING_MAP (see §8) |
| `book_page_count` | `page_count` | `page_count` | `INT` | Validated: 1-50,000 |
| `book_lang[0]` | `language_code` | `language_code` | `CHAR(3)` | Mapped via LANGUAGE_MAP (see §7) |
| `book_publisher_label[0].label` | `publisher_name` | `publisher_name` | `VARCHAR(300)` | First publisher from array |
| `status` | `publishing_status_code` | `publishing_status_code` | `CHAR(2)` | "disabled"→"08", else→"04" |
| `book_publication_year` / `book_year` | `publication_date` | `publication_date` | `DATE` | Parsed from YYYY or YYYY-MM-DD |
| `status != 'disabled'` | `is_active` | `is_active` | `BOOLEAN` | Active/inactive flag |
| `created_at` | `source_created_at` | — | — | Stored in metadata |
| `updated_at` | `source_updated_at` | — | — | Used for `updated_at` |
| — | — | `created_at` | `TIMESTAMPTZ` | Auto-generated |
| — | — | `updated_at` | `TIMESTAMPTZ` | Auto-updated |

### Extraction Functions

```python
# ISBN extraction priority (data_adapter.py:extract_identifier)
1. raw_data['barcode']           # Most reliable
2. raw_data['book_isbn']         # Fallback
3. raw_data['book_isbn_label'][0]['label']  # Legacy format

# Publisher extraction (data_adapter.py:_extract_label)
book_publisher_label[0].label → publisher_name
```

---

## 2. Contributors (Authors/Translators)

**Source**: `author_label[]`, `book_translator_label[]`  
**Target Table**: `Contributor`

| Yakaboo JSON Field | ProductDTO Field | DB Column | DB Type | Notes |
|-------------------|------------------|-----------|---------|-------|
| `author_label[n].label` | `person_name` | `person_name` | `VARCHAR(300)` | Display name |
| `author_label[n].option_id` | `source_id` | — | — | Stored in metadata |
| — | `role_code` | `role_code` | `VARCHAR(3)` | "A01" for authors |
| — | `sequence_number` | `sequence_number` | `INT` | 1-based index |
| — | `contributor_type` | `contributor_type` | `CHAR(1)` | Always "P" (Person) |
| `book_translator_label[n].label` | `person_name` | `person_name` | `VARCHAR(300)` | Translator name |
| — | `role_code` | `role_code` | `VARCHAR(3)` | "B06" for translators |

### Role Codes (ONIX List 17)

| Code | Role | Yakaboo Source |
|------|------|----------------|
| `A01` | Author | `author_label[]` |
| `B06` | Translator | `book_translator_label[]` |
| `A12` | Illustrator | — (not mapped) |
| `E07` | Narrator | — (not mapped) |

### Example Transform

```python
# Input (Yakaboo JSON)
{
  "author_label": [
    {"option_id": "123", "label": "Тарас Шевченко"},
    {"option_id": "456", "label": "Іван Франко"}
  ],
  "book_translator_label": [
    {"option_id": "789", "label": "Микола Лукаш"}
  ]
}

# Output (ContributorDTO → Contributor records)
[
  {role_code: "A01", sequence_number: 1, person_name: "Тарас Шевченко"},
  {role_code: "A01", sequence_number: 2, person_name: "Іван Франко"},
  {role_code: "B06", sequence_number: 3, person_name: "Микола Лукаш"}
]
```

---

## 3. Subjects (Categories/Keywords)

**Source**: `category_ids[]`, `keywords`  
**Target Table**: `Subject`

| Yakaboo JSON Field | ProductDTO Field | DB Column | DB Type | Notes |
|-------------------|------------------|-----------|---------|-------|
| `category_ids[n]` | `subject_code` | `subject_code` | `VARCHAR(100)` | Category ID as string |
| — | `scheme_code` | `scheme_code` | `VARCHAR(10)` | "24" (Proprietary) |
| — | `subject_heading_text` | `subject_heading_text` | `VARCHAR(500)` | "Yakaboo Category {id}" |
| — | `is_primary` | `is_primary` | `BOOLEAN` | First category = true |
| `keywords` | `subject_heading_text` | `subject_heading_text` | `VARCHAR(500)` | Individual keyword |
| — | `scheme_code` | `scheme_code` | `VARCHAR(10)` | "20" (Keywords) |

### Scheme Codes (ONIX List 27)

| Code | Scheme | Yakaboo Source |
|------|--------|----------------|
| `10` | BISAC | — (not mapped) |
| `12` | BIC | — (not mapped) |
| `20` | Keywords | `keywords` (comma-split) |
| `24` | Proprietary | `category_ids[]` |
| `93` | THEMA | — (future enrichment) |

### Limits Applied

- **Categories**: Max 10 per product
- **Keywords**: Max 20 per product, each max 500 chars

### Example Transform

```python
# Input (Yakaboo JSON)
{
  "category_ids": [100500, 100501, 100502],
  "keywords": "українська література, класика, поезія, романтизм"
}

# Output (SubjectDTO → Subject records)
[
  {scheme_code: "24", subject_code: "100500", subject_heading_text: "Yakaboo Category 100500", is_primary: true},
  {scheme_code: "24", subject_code: "100501", subject_heading_text: "Yakaboo Category 100501", is_primary: false},
  {scheme_code: "24", subject_code: "100502", subject_heading_text: "Yakaboo Category 100502", is_primary: false},
  {scheme_code: "20", subject_heading_text: "українська література"},
  {scheme_code: "20", subject_heading_text: "класика"},
  {scheme_code: "20", subject_heading_text: "поезія"},
  {scheme_code: "20", subject_heading_text: "романтизм"}
]
```

---

## 4. Text Content (Descriptions)

**Source**: `description`, `short_description`  
**Target Table**: `TextContent`

| Yakaboo JSON Field | ProductDTO Field | DB Column | DB Type | Notes |
|-------------------|------------------|-----------|---------|-------|
| `description` | `content` | `content` | `TEXT` | HTML tags stripped |
| — | `text_type_code` | `text_type_code` | `CHAR(2)` | "03" (Main description) |
| `short_description` | `content` | `content` | `TEXT` | Only if differs from main |
| — | `text_type_code` | `text_type_code` | `CHAR(2)` | "02" (Short description) |

### Text Type Codes (ONIX List 153)

| Code | Type | Yakaboo Source |
|------|------|----------------|
| `02` | Short description | `short_description` |
| `03` | Main description | `description` |
| `04` | Table of contents | — (not mapped) |
| `06` | Review quote | — (not mapped) |
| `13` | Biographical note | — (not mapped) |

### HTML Cleaning

```python
# All HTML tags are stripped via regex
content = re.sub(r'<[^>]+>', '', raw_html).strip()
```

---

## 5. Media Files (Images)

**Source**: `image`, `mediagallery_image[]`  
**Target Table**: `MediaFile`

| Yakaboo JSON Field | ProductDTO Field | DB Column | DB Type | Notes |
|-------------------|------------------|-----------|---------|-------|
| `image` | `file_link` | `file_link` | `TEXT` | Main cover image |
| — | `resource_content_type_code` | `resource_content_type_code` | `CHAR(2)` | "01" (Front cover) |
| — | `resource_mode_code` | `resource_mode_code` | `CHAR(2)` | "03" (Image) |
| `mediagallery_image[n]` | `file_link` | `file_link` | `TEXT` | Gallery images |
| — | `resource_content_type_code` | `resource_content_type_code` | `CHAR(2)` | "02" (Additional) |

### Resource Content Type Codes (ONIX List 158)

| Code | Type | Source |
|------|------|--------|
| `01` | Front cover | `image` |
| `02` | Additional image | `mediagallery_image[]` |

### Resource Mode Codes (ONIX List 159)

| Code | Mode | Used |
|------|------|------|
| `03` | Image | Yes |
| `06` | Video | Not mapped |
| `07` | Audio | Not mapped |

### URL Normalization

```python
# Relative URLs are prefixed with base domain
if not url.startswith('http'):
    url = f"https://yakaboo.ua{url}"
```

### Limits Applied

- **Gallery images**: Max 10 per product
- **Duplicates**: Main image excluded from gallery

---

## 6. Prices

**Source**: `price`, `original_price`, `for_filter_is_in_stock`  
**Target Table**: `Price` (via `PriceSource`)

| Yakaboo JSON Field | ProductDTO Field | DB Column | DB Type | Notes |
|-------------------|------------------|-----------|---------|-------|
| `price` | `price_amount` | `price_amount` | `DECIMAL(12,2)` | Current price |
| `original_price` | `original_price` | — | — | Used for discount calc |
| — | `discount_percent` | `discount_percent` | `DECIMAL(5,2)` | Calculated: `(orig-price)/orig*100` |
| — | `price_type_code` | `price_type_code` | `CHAR(2)` | "02" (RRP incl. tax) |
| — | `currency_code` | `currency_code` | `CHAR(3)` | "UAH" |
| `for_filter_is_in_stock` | `in_stock` | `stock_quantity` | `INT` | "0"→NULL, else→1 |
| — | `source_code` | `source_id` | `INT` | FK to PriceSource |
| — | `recorded_at` | `recorded_at` | `TIMESTAMPTZ` | Import timestamp |

### Price Type Codes (ONIX List 58)

| Code | Type | Used |
|------|------|------|
| `01` | RRP excluding tax | Not used |
| `02` | RRP including tax | Yes (default) |
| `41` | Promotional price | Not used |

### Discount Calculation

```python
if original_price and original_price > current_price:
    discount_percent = ((original_price - current_price) / original_price * 100)
```

### Example Transform

```python
# Input (Yakaboo JSON)
{
  "price": 350.00,
  "original_price": 500.00,
  "for_filter_is_in_stock": "1"
}

# Output (PriceDTO → Price record)
{
  price_type_code: "02",
  price_amount: 350.00,
  currency_code: "UAH",
  discount_percent: 30.00,
  stock_quantity: 1,
  source_id: <PriceSource.id for "yakaboo">
}
```

---

## 7. Language Code Mapping

**Location**: `data_adapter.py:LANGUAGE_MAP`

| Yakaboo ID | ISO 639-2 | Language |
|------------|-----------|----------|
| `332272` | `ukr` | Ukrainian 🇺🇦 |
| `332273` | `rus` | Russian |
| `332271` | `eng` | English (old) |
| `332987` | `eng` | English (main) |
| `332274` | `pol` | Polish |
| `332275` | `deu` | German |
| `332276` | `fra` | French |
| *default* | `ukr` | Ukrainian (fallback) |

### Source Field

```python
# Yakaboo JSON structure
{
  "book_lang": [332272]  # Array of language IDs
}

# Mapping (first element only)
language_code = LANGUAGE_MAP.get(book_lang[0], 'ukr')
```

---

## 8. Product Form (Binding) Mapping

**Location**: `data_adapter.py:BINDING_MAP`

| Yakaboo Label Contains | ONIX Code | Product Form |
|-----------------------|-----------|--------------|
| `тверд` | `BB` | Hardback |
| `hard` | `BB` | Hardback |
| `м'як` | `BC` | Paperback |
| `мяг` | `BC` | Paperback |
| `paper` | `BC` | Paperback |
| `soft` | `BC` | Paperback |
| `інтег` | `BB` | Hardback (integral) |
| *default* | `BB` | Hardback |

### Source Field

```python
# Yakaboo JSON structure
{
  "book_binding_type_label": [
    {"option_id": "123", "label": "Тверда палітурка"}
  ]
}

# Mapping (case-insensitive substring match)
for key, form in BINDING_MAP.items():
    if key in binding_label.lower():
        return form
```

---

## 9. Publishing Status Mapping

| Yakaboo Status | ONIX Code | Status Name |
|----------------|-----------|-------------|
| `disabled` | `08` | Inactive |
| `0` | `08` | Inactive |
| *any other* | `04` | Active |

### ONIX List 64 Reference

| Code | Status |
|------|--------|
| `00` | Unspecified |
| `01` | Cancelled |
| `02` | Forthcoming |
| `03` | Postponed |
| `04` | **Active** ✓ |
| `05` | No longer available |
| `06` | Out of stock |
| `07` | Out of print |
| `08` | **Inactive** ✓ |

---

## 10. Metadata (JSON Field)

Extra Yakaboo fields stored in `CatalogProduct.metadata` JSONB column:

| Yakaboo Field | Metadata Key | Description |
|---------------|--------------|-------------|
| `id` | `yakaboo_id` | Yakaboo internal numeric ID |
| `sku` | `yakaboo_sku` | Yakaboo SKU string |
| `url_key` | `url_key` | URL slug for product page |
| `category_ids` | `category_ids` | Full array of category IDs |
| `statistics_visits` | `statistics_visits` | Page view count |
| `is_top_sale` | `is_top_sale` | Bestseller flag |

### Example Metadata

```json
{
  "yakaboo_id": 1234567,
  "yakaboo_sku": "UA-000123456",
  "url_key": "taras-shevchenko-kobzar",
  "category_ids": [100500, 100501, 100502, 100503],
  "statistics_visits": 15420,
  "is_top_sale": true
}
```

---

## 📊 Field Coverage Summary

| Category | Yakaboo Fields | Mapped Fields | Coverage |
|----------|----------------|---------------|----------|
| **Identifiers** | 4 | 4 | 100% |
| **Title/Description** | 3 | 3 | 100% |
| **Physical** | 1 | 1 | 100% |
| **Contributors** | 2 | 2 | 100% |
| **Categories** | 2 | 2 | 100% |
| **Media** | 2 | 2 | 100% |
| **Pricing** | 3 | 3 | 100% |
| **Language** | 1 | 1 | 100% |
| **Publisher** | 1 | 1 | 100% |
| **Dates** | 2 | 2 | 100% |
| **Status** | 1 | 1 | 100% |

---

## 🔗 Related Files

| File | Purpose |
|------|---------|
| [app/adapters/data_adapter.py](../app/adapters/data_adapter.py) | Transformation logic |
| [app/schemas/data_models.py](../app/schemas/data_models.py) | DTO definitions |
| [prisma/schema.prisma](../prisma/schema.prisma) | Database schema |
| [app/services/prisma_ingestion_service.py](../app/services/prisma_ingestion_service.py) | Import logic |
| [YAKABOO_DATA_STRUCTURE.md](./YAKABOO_DATA_STRUCTURE.md) | Raw field analysis |
| [YAKABOO_ONIX_MAPPING.md](./YAKABOO_ONIX_MAPPING.md) | ONIX code reference |

---

*Last updated: 2026-01-10*
