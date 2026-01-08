# Yakaboo to ONIX Mapping Status

## Overview
This document tracks the mapping between Yakaboo raw JSON fields and ONIX 3.0 Standard.

## Status: ACTIVE MIGRATION (Jan 2026)
- **Phase 1: Skeleton** (Completed) - IDs, Title, Price, Stock.
- **Phase 2: Full Object** (In Progress) - Authors, Descriptions, Subjects, Publishers.

## Field Mapping Table

| Yakaboo Field | ONIX Entity | ONIX Field | Logic/Transformation |
|---|---|---|---|
| `id` | `CatalogProduct` | `record_reference` | Prefix `yakaboo_` + ID |
| `book_isbn` | `CatalogProduct` | `isbn_13` | Clean hyphens. |
| `name` | `CatalogTitle` | `title_text` | Type=01 (Distinctive). |
| `author_label` | `Contributor` | `name` | Iterate array. Role=A01 (Author). |
| `book_publisher_label` | `Publisher` | `name` | Extract `label`. |
| `description` | `TextContent` | `text` | Type=03 (Main Description). HTML allowed. |
| `book_page_count` | `CatalogExtent` | `value` | Type=00 (Main Page Count). |
| `book_binding` | `CatalogMeasure` | `measurement` | Parse "145x200 mm" -> Height/Width. |
| `book_lang_label` | `CatalogLanguage` | `code` | Map "Украинский" -> "ukr". |
| `category` | `CatalogSubject` | `subject_heading_text` | Use full breadcrumb path. |

## Critical Data Structures
Yakaboo uses a "EAV-like" structure where `*_label` fields contain the human-readable text.
**ALWAYS** prefer `*_label` arrays over raw ID arrays (e.g., use `author_label` not `author`).

### Example `author_label`
```json
[
  {
    "label": "Stephen King",
    "option_code": "stephen_king"
  }
]
```