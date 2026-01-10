# Yakaboo → Database Quick Mapping

Simple table showing ALL field mappings from Yakaboo JSON to PostgreSQL.

**ORM**: Prisma (see `prisma/schema.prisma`)

---

## Main Product (`catalog_products`)

| Yakaboo JSON | → | DB Column |
|--------------|---|-----------|
| `barcode` / `book_isbn` / `book_isbn_label[0].label` | → | `isbn13` |
| `sku` | → | `proprietary_id` |
| `name` | → | `title` |
| `short_description` | → | `subtitle` |
| `book_binding_type_label[0].label` | → | `product_form_code` |
| `book_page_count` | → | `page_count` |
| `book_lang[0]` | → | `language_code` |
| `book_publisher_label[0].label` | → | `publisher_name` |
| `status` | → | `publishing_status_code` |
| `book_publication_year` / `book_year` | → | `publication_date` |
| `status != 'disabled'` | → | `is_active` |
| `id`, `sku`, `url_key`, `category_ids`, etc. | → | `metadata` (JSON) |

---

## Contributors N:N (`Contributor` + `ProductContributor`)

| Yakaboo JSON | → | DB Table / Column |
|--------------|---|-----------|
| `author_label[n].label` | → | `Contributor.person_name` |
| `author_label[n].option_id` | → | `Contributor.yakaboo_option_id` |
| `book_translator_label[n].label` | → | `Contributor.person_name` |
| — | → | `ProductContributor.role_code` (A01=author, B06=translator) |
| — | → | `ProductContributor.sequence_number` (1,2,3...) |
| — | → | `Contributor.contributor_type` (always "P"=Person) |

**Unique constraint**: One `Contributor` per person, linked to products via `ProductContributor`.

---

## Subjects N:N (`Subject` + `ProductSubject`)

| Yakaboo JSON | → | DB Table / Column |
|--------------|---|-----------|
| `category_ids[n]` | → | `Subject.subject_code` (scheme=24) |
| `keywords` (comma-split) | → | `Subject.subject_heading_text` (scheme=20) |
| — | → | `Subject.scheme_code` (20=keywords, 24=proprietary) |
| — | → | `ProductSubject.is_primary` (first category=true) |
| — | → | `ProductSubject.sequence_number` |

**Unique constraint**: One `Subject` per (scheme_code, subject_code, heading_text), linked via `ProductSubject`.

---

## Text Content (`TextContent`)

| Yakaboo JSON | → | DB Column |
|--------------|---|-----------|
| `description` | → | `content` (type=03 main) |
| `short_description` | → | `content` (type=02 short) |
| — | → | `text_type_code` (02=short, 03=main) |

---

## Media Files (`MediaFile`)

| Yakaboo JSON | → | DB Column |
|--------------|---|-----------|
| `image` | → | `file_link` (type=01 front cover) |
| `mediagallery_image[n]` | → | `file_link` (type=02 additional) |
| — | → | `resource_content_type_code` (01/02) |
| — | → | `resource_mode_code` (03=image) |
| — | → | `sequence_number` (1,2,3...) |

---

## Prices (`Price`)

| Yakaboo JSON | → | DB Column |
|--------------|---|-----------|
| `price` | → | `price_amount` |
| `original_price` | → | `discount_percent` (calculated %) |
| `for_filter_is_in_stock` | → | `stock_quantity` |
| — | → | `price_type_code` (02=RRP incl tax) |
| — | → | `currency_code` (UAH) |
| — | → | `source_id` (FK → PriceSource) |
| — | → | `recorded_at` (import timestamp) |

---

## Language Codes

| Yakaboo ID | → | ISO Code | Language |
|------------|---|----------|----------|
| `332272` | → | `ukr` | Ukrainian 🇺�� |
| `332273` | → | `rus` | Russian |
| `332987` | → | `eng` | English |
| `332271` | → | `eng` | English (old) |
| `332274` | → | `pol` | Polish |
| `332275` | → | `deu` | German |
| `332276` | → | `fra` | French |
| *default* | → | `ukr` | Ukrainian (fallback) |

---

## Binding → Product Form (ONIX)

| Yakaboo Label Contains | → | ONIX Code | Meaning |
|------------------------|---|-----------|---------|
| тверд, hard, інтег | → | `BB` | Hardback |
| м'як, мяг, paper, soft | → | `BC` | Paperback |
| *default* | → | `BB` | Hardback |

---

## Status Mapping

| Yakaboo Status | → | ONIX Code | Meaning |
|----------------|---|-----------|---------|
| `disabled` | → | `08` | Inactive |
| `0` | → | `08` | Inactive |
| *any other* | → | `04` | Active |

---

## Metadata JSON (stored in `catalog_products.metadata`)

| Yakaboo Field | Stored As |
|---------------|-----------|
| `id` | `yakaboo_id` |
| `sku` | `yakaboo_sku` |
| `url_key` | `url_key` |
| `category_ids` | `category_ids` |
| `statistics_visits` | `statistics_visits` |
| `is_top_sale` | `is_top_sale` |

---

*See [YAKABOO_TO_DB_MAPPING.md](YAKABOO_TO_DB_MAPPING.md) for detailed documentation with examples.*
