# Data Examples

## 1. Catalog Product (SQL Model)

Representation of a book in `catalog_products` and related tables.

```python
# Main Entry
product = CatalogProduct(
    isbn_13="9786175000001",
    title="Тіні забутих предків",
    product_form=ProductForm.HARDCOVER, # "BB"
    publishing_status=PublishingStatus.ACTIVE, # "04"
    is_ukrainian=True,
    publisher_id="...",
    
    # JSONB Dump (Optional, for full fidelity)
    onix_full={
        "RecordReference": "...",
        "ProductIdentifier": [...]
    }
)

# Relations (Created automatically via ORM)
title_original = CatalogTitle(
    type=TitleType.ORIGINAL_TITLE, 
    text="Тіні забутих предків"
)

author = CatalogProductContributor(
    role=ContributorRole.AUTHOR, # "A01"
    person_name="Михайло Коцюбинський"
)

extent = CatalogExtent(
    type=ExtentType.MAIN_PAGE_COUNT, 
    value=320, 
    unit="pages"
)
```

## 2. Market Offer (Dynamic Price)

Representation of a price in `offers` table.

```python
offer = Offer(
    book_id="... (UUID of CatalogProduct)",
    supplier_id="... (UUID of Yakaboo)",
    
    sku="123456", # Yakaboo internal ID
    url="https://yakaboo.ua/ua/book/...",
    
    price=450.00,
    price_old=500.00,
    currency="UAH",
    
    in_stock=True,
    availability=ProductAvailability.IN_STOCK, # "21"
    
    last_updated="2026-01-03T12:00:00Z"
)
```

## 3. ONIX Code Lists (Enums)

We use strict Enums defined in `app/models/codes.py`.

*   **ProductForm**: `BOOK` (BA), `EBOOK` (EA), `AUDIO` (AA).
*   **ContributorRole**: `AUTHOR` (A01), `TRANSLATOR` (B06), `ILLUSTRATOR` (A12).
*   **PublishingStatus**: `ACTIVE` (04), `FORTHCOMING` (02), `OUT_OF_PRINT` (07).
