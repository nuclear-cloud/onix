# Архітектура ONIX Catalog

## Database Diagram (DBML)

```dbml
// ========== REFERENCE DATA (Довідники) ==========

Table ref_onix_codelists {
  list_number Integer [pk]
  code String [pk]
  description Text [null]
  label_en String [null]
  label_uk String [null]
  is_active Boolean [default: true]
  
  Indexes {
    list_number
  }
}

Table ref_thema_subjects {
  code String [pk]
  parent_code String [fk: ref_thema_subjects.code, null]
  label_en String
  label_uk String [null]
  description_en Text [null]
  description_uk Text [null]
  is_active Boolean [default: true]
  
  Indexes {
    (code, parent_code)  // FK constraint
    label_uk  // Ukrainian sorting
  }
}

// ========== MASTER DATA (Основні таблиці) ==========

Table catalog_publishers {
  id UUID [pk]
  name String [unique]
  gln String [null]
}

Table catalog_products {
  id UUID [pk]
  record_reference String [unique, not null]
  isbn_13 String [unique, null]
  ean String [unique, null]
  sku String [null]
  
  product_form String [ref: - ref_onix_codelists.code]
  product_form_detail String [null]
  publishing_status String [ref: - ref_onix_codelists.code]
  is_ukrainian Boolean [default: true]
  
  publisher_id UUID [ref: - catalog_publishers.id, null]
  created_at DateTime
  updated_at DateTime
  
  Indexes {
    isbn_13
    product_form
    is_ukrainian
    created_at
  }
}

// ========== CONTRIBUTORS & RELATIONSHIPS ==========

Table catalog_contributors {
  id UUID [pk]
  name String [not null]
  person_name_inverted String [null]
  biographical_note Text [null]
  
  Indexes {
    name
  }
}

Table catalog_product_contributors_link {
  product_id UUID [pk, ref: - catalog_products.id]
  contributor_id UUID [pk, ref: - catalog_contributors.id]
  role String [pk, ref: - ref_onix_codelists.code]
  sequence_number Integer [default: 1]
}

Table catalog_collections {
  id UUID [pk]
  title String [not null]
  type String [null]
  issn String [null]
  
  Indexes {
    title
  }
}

Table catalog_product_collections_link {
  product_id UUID [pk, ref: - catalog_products.id]
  collection_id UUID [pk, ref: - catalog_collections.id]
  sequence_type String [null]
  sequence_number String [null]
}

// ========== PRODUCT DETAILS ==========

Table catalog_titles {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  type String [ref: - ref_onix_codelists.code]
  title_text Text [not null]
  subtitle Text [null]
}

Table catalog_languages {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  role String [null]
  code String [not null]  // ISO 639-2
}

Table catalog_subjects {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  scheme_identifier String [not null]  // 93 = Thema
  subject_code String [null]
  subject_heading_text String [null]
  
  Note: 'subject_code может быть FK к ref_thema_subjects.code'
}

Table catalog_extents {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  type String [ref: - ref_onix_codelists.code]
  value Decimal [not null]
  unit String [null]  // Pages, Hours
}

Table catalog_measures {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  type String [ref: - ref_onix_codelists.code]  // Height, Width, Weight
  measurement Decimal [not null]
  unit_code String [ref: - ref_onix_codelists.code]  // mm, gr
}

Table catalog_audience_ranges {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  qualifier String [null]
  precision String [null]
  value String [not null]
}

Table catalog_prizes {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  name String [not null]
  year String [null]
  country String [null]
  code String [null]
}

// ========== CONTENT & DESCRIPTIONS ==========

Table catalog_text_contents {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  type String [ref: - ref_onix_codelists.code]  // Blurb, Description
  text Text [not null]
  author String [null]
}

Table catalog_cited_contents {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  type String [not null]  // Review, Quote
  source_title String [null]
  citation_note Text [null]
  link String [null]
}

Table catalog_related_products {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  relation_code String [ref: - ref_onix_codelists.code]
  related_product_id_type String [default: "15"]  // ISBN
  related_product_id_value String [not null]
}

Table catalog_publishing_dates {
  id UUID [pk]
  product_id UUID [ref: - catalog_products.id]
  role String [ref: - ref_onix_codelists.code]  // Publication, Update
  date_value String [not null]  // YYYYMMDD
  date_format String [default: "00"]
}
```

---

## Entity Relationship Diagram (Text)

```
┌──────────────────────────────────────────────────────────────┐
│                    REFERENCE DATA                             │
├──────────────────────────────────────────────────────────────┤
│  ref_onix_codelists          ref_thema_subjects              │
│  ├─ list_number [PK]         ├─ code [PK]                    │
│  ├─ code [PK]                ├─ parent_code [FK self]        │
│  ├─ description              ├─ label_uk                     │
│  ├─ label_en, label_uk       ├─ is_active                    │
│  └─ is_active                └─ (children hierarchy)         │
│                                                               │
│  4,748 ONIX codes            9,187 THEMA codes              │
│  Flat structure              3-level hierarchy               │
└──────────────────────────────────────────────────────────────┘
         ↓              ↓              ↓
    (FK links)    (FK links)    (FK links)
         ↓              ↓              ↓
┌──────────────────────────────────────────────────────────────┐
│              MASTER CATALOG (catalog_products)               │
├──────────────────────────────────────────────────────────────┤
│  id [UUID]                                                   │
│  record_reference, isbn_13, ean, sku                        │
│  product_form, publishing_status (FK → ONIX)                │
│  publisher_id (FK → catalog_publishers)                     │
│  is_ukrainian, created_at, updated_at                       │
│                                                              │
│  100 записів (тестові)                                      │
└──────────────────────────────────────────────────────────────┘
       │       │       │       │       │       │       │
       ├─────┬─┴──┬────┼────┬─┴───┬───┤
       │     │    │    │    │     │   │
       ▼     ▼    ▼    ▼    ▼     ▼   ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Titles   │ │Language  │ │Subjects  │ │Contributors │
│(titles)  │ │(lang)    │ │(subj)    │ │(link)        │
│100 rows  │ │          │ │(→THEMA)  │ │              │
└──────────┘ └──────────┘ └──────────┘ └──────────────┘

     ▼            ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Extents  │ │Measures  │ │Audience  │ │Prizes        │
│ (pages)  │ │(size)    │ │ (age)    │ │(awards)      │
└──────────┘ └──────────┘ └──────────┘ └──────────────┘

     ▼            ▼            ▼            ▼
┌──────────────────────────────────────────────────────┐
│TextContent  CitedContent  RelatedProducts  Dates   │
│(blurbs)     (reviews)     (ebook,audio)   (pub)    │
└──────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
JSON FILES (data/)
├─ ONIX_BookProduct_Codelists_Issue_71.json (4,748 codes)
└─ thema_v1.6_uk.json (9,187 codes)
       │
       ▼
scripts/load_reference_codes.py
├─ load_onix_codelists()
│  └─ Flat structure → batch INSERT...ON CONFLICT
│
└─ load_thema_codes()
   ├─ Build parent_to_children adjacency list
   ├─ BFS traversal from roots
   ├─ Group records by level (0, 1, 2, ...)
   └─ Batch INSERT level-by-level
          (Гарантує: батьки перед дітьми)
       │
       ▼
PostgreSQL 16.11
├─ ref_onix_codelists (4,748 ✅)
├─ ref_thema_subjects (9,187 ✅)
│  └─ Self-referential hierarchy (parent_code FK)
│
└─ catalog_products (100 тестових)
   ├─ catalog_titles (100)
   ├─ catalog_subjects (→ ref_thema)
   ├─ catalog_contributors (0)
   └─ ... (18 деталізованих таблиць)
       │
       ▼
app/services/catalog_loader.py
├─ CatalogLoader.get_thema_cache()
│  └─ Cache TTL: 3600 seconds (1 hour)
├─ ProductMerger.DOMAIN_PRIORITY
│  └─ Дедублікація між джерелами
└─ Validation against ONIX codes
```

---

## Query Patterns

### 1️⃣ Пошук книг за THEMA кодом

```python
# Find all Ukrainian children books
query = select(CatalogProduct).join(
    CatalogSubject,
    CatalogProduct.id == CatalogSubject.product_id
).join(
    RefThemaSubject,
    CatalogSubject.subject_code == RefThemaSubject.code
).where(
    RefThemaSubject.code.like("Y%")  # Y = Children
)
```

### 2️⃣ Отримати книгу з усіма деталями

```python
product = session.execute(
    select(CatalogProduct)
    .options(
        selectinload(CatalogProduct.titles),
        selectinload(CatalogProduct.subjects),
        selectinload(CatalogProduct.languages),
        selectinload(CatalogProduct.publisher)
    )
    .where(CatalogProduct.isbn_13 == "978-...")
).scalar()
```

### 3️⃣ Ієрархія THEMA кодів

```python
# Get all descendants of "Y" (Children books)
def get_descendants(code):
    parent = session.get(RefThemaSubject, code)
    if parent:
        return [parent] + sum(
            [get_descendants(c.code) for c in parent.children],
            []
        )
    return []
```

---

## Performance Considerations

| Operation | Time | Notes |
|-----------|------|-------|
| Load ONIX (4,748 codes) | ~100ms | 5 batches |
| Load THEMA (9,187 codes) | ~800ms | BFS + 10 levels |
| Cache THEMA codes | ~50ms | In-memory, TTL 1h |
| Search by ISBN | <10ms | Index on isbn_13 |
| Search by THEMA | <50ms | Join + index |

---

## Constraints & Rules

### Primary Keys
- `ref_onix_codelists`: Composite `(list_number, code)`
- `ref_thema_subjects`: Simple `code` with hierarchical FK
- All other entities: UUID

### Foreign Keys (Cascade Delete)
- `catalog_products` → publishers (soft constraint)
- All detail tables → products (hard cascade)

### Indexes
- `ref_onix_codelists(list_number)`
- `ref_thema_subjects(label_uk)` - Ukrainian sorting
- `catalog_products(isbn_13, is_ukrainian, created_at)`
- `catalog_titles(product_id)`
- `catalog_subjects(product_id, scheme_identifier)`

### Soft Delete
- `is_active BOOLEAN DEFAULT true`
- Missing records updated to `is_active=FALSE`
- Preserved for audit trail

---

**Diagram Version**: 1.0  
**Updated**: January 6, 2026
