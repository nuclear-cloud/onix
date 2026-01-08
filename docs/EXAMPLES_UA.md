# Приклади Даних

## 1. Продукт Каталогу (SQL Модель)

Представлення книги в `catalog_products` та пов'язаних таблицях.

```python
# Головний запис
product = CatalogProduct(
    isbn_13="9786175000001",
    title="Тіні забутих предків",
    product_form=ProductForm.HARDCOVER, # "BB"
    publishing_status=PublishingStatus.ACTIVE, # "04"
    is_ukrainian=True,
    publisher_id="...",
    
    # JSONB Дамп (Опціонально, для повної точності)
    onix_full={
        "RecordReference": "...",
        "ProductIdentifier": [...]
    }
)

# Зв'язки (Створюються автоматично через ORM)
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

## 2. Ринкова Пропозиція (Динамічна Ціна)

Представлення ціни в таблиці `offers`.

```python
offer = Offer(
    book_id="... (UUID of CatalogProduct)",
    supplier_id="... (UUID of Yakaboo)",
    
    sku="123456", # Внутрішній ID Yakaboo
    url="https://yakaboo.ua/ua/book/...",
    
    price=450.00,
    price_old=500.00,
    currency="UAH",
    
    in_stock=True,
    availability=ProductAvailability.IN_STOCK, # "21"
    
    last_updated="2026-01-03T12:00:00Z"
)
```

## 3. ONIX Списки Кодів (Enums)

Ми використовуємо суворі Enums визначені в `app/models/codes.py`.

*   **ProductForm**: `BOOK` (BA), `EBOOK` (EA), `AUDIO` (AA).
*   **ContributorRole**: `AUTHOR` (A01), `TRANSLATOR` (B06), `ILLUSTRATOR` (A12).
*   **PublishingStatus**: `ACTIVE` (04), `FORTHCOMING` (02), `OUT_OF_PRINT` (07).
