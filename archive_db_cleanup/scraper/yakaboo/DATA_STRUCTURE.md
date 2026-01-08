# Yakaboo Data Structure & Mapping Guide

**Last Updated:** 2026-01-05
**Source File:** `data/yakaboo_complete_final.jsonl`

This document describes the internal structure of Yakaboo's JSONL data and the mapping logic required to convert it into ONIX 3.0.

## 1. Core Concept: IDs vs Labels
Yakaboo uses a strict EAV (Entity-Attribute-Value) model. Most categorical fields in the root object contain **internal IDs**, not human-readable text.

*   **Rule**: Always prefer `*_label` arrays over root fields for text values.
*   **Pattern**:
    *   `author` (IDs: `[123, 456]`) -> `author_label` (`[{"label": "King", ...}, ...]`)
    *   `book_publisher` (ID: `999`) -> `book_publisher_label` (`[{"label": "Vivat", ...}]`)
    *   `book_binding_type` (ID) -> `book_binding_type_label` (`[{"label": "Тверда", ...}]`)

## 2. Field Analysis & Mapping

### A. Identification
| Yakaboo Field | ONIX Tag | Notes |
| :--- | :--- | :--- |
| `id` | `RecordReference` | Internal ID. |
| `book_isbn` | `ProductIdentifier` (Type 15) | Valid ISBN-13 (93.5% coverage). Strip hyphens. |
| `sku` | `ProductIdentifier` (Type 01) | Yakaboo SKU. |
| `barcode` | `ProductIdentifier` (Type 03) | GTIN-13 (often same as ISBN). |

### B. Product Form & Binding
We discovered two distinct fields governing the physical format:

1.  **`book_binding_type_label`**: The **Category**.
    *   Values: "Тверда", "М'яка", "Інтегральна", "На пружині".
    *   **Mapping**: Maps to `<ProductForm>` (BB, BC) and `<ProductFormDetail>` (B106, B108).
2.  **`book_binding`**: The **Dimensions** (Text).
    *   Values: "145x200 мм", "205x260 мм".
    *   **Action**: Must be parsed via Regex `(\d+)x(\d+)` to extract `<Measure>` (Width/Height).

### C. Contributors (Authors, etc.)
*   **Source**: `author_label` (Array of objects).
*   **Field**: `label`.
*   **Mapping**: `<Contributor>` with Role `A01` (Author).
*   **Translators**: `book_translator` / `book_translator_label`.

### D. Language
*   **Source**: `book_lang_label` -> `label` or `option_code`.
*   **Anomaly**: ~89% of catalog is "Anglijskij" (English).
*   **Mapping**:
    *   `Anglijskij` -> `eng`
    *   `Ukrainskij` -> `ukr`

### E. Extents (Pages)
*   **Source**: `book_page_count`.
*   **Mapping**: `<Extent>` with Type `00` (Main content page count) and Unit `03` (Pages).

### F. Description
*   **Source**: `description`.
*   **Format**: **HTML** (Contains `<p>`, `<br>`, `<ul>`).
*   **Mapping**: `<TextContent>` with `textformat="05"` (XHTML).

## 3. Classification (Books vs Non-Books)
The dataset includes non-book items. Filter logic:
*   **Is Book**: Has `book_isbn` OR Category L2 = "Книги".
*   **Is Gift/Game**: Has keys starting with `gift_`, `boardgame_`.
    *   Action: Exclude or map to `ProductForm` = `00` (Undefined) / `ZE` (Game).

## 4. Prices & Stock
*   **Price**: `price` (Float, UAH).
*   **Stock**: `is_in_stock` (Bool).
    *   True -> `<ProductAvailability>` = `21` (In Stock).
    *   False -> `<ProductAvailability>` = `40` (Not in Stock).

## 5. Known Issues
*   **Missing Dimensions**: If `book_binding` doesn't contain regex match, dimensions are unknown.
*   **Messy Editions**: `book_edition` is free text ("2nd edition", "Revised").
