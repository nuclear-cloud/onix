"""
Конфігурація Мапінгу Yakaboo -> ONIX 3.0.

Цей файл визначає, з яких полів сирого JSON Yakaboo ми беремо дані для заповнення
полів стандарту ONIX.

Легенда:
- `source_field`: Основне поле в JSON Yakaboo.
- `fallback_field`: Запасне поле, якщо основне порожнє.
- `label_suffix`: Якщо True, шукати значення в масиві `_label` (наприклад, `author_label`).
"""

YAKABOO_MAPPING = {
    # --- 1. Ідентифікатори (Product Identifier) ---
    "identifiers": {
        # ISBN-13: Унікальний номер книги (13 цифр).
        # Джерело: поле "book_isbn" або "book_isbn_label".
        "isbn13": "book_isbn",
        
        # Barcode/EAN: Штрих-код товару.
        # Джерело: поле "barcode".
        "barcode": "barcode",
        
        # Внутрішній ID Yakaboo.
        "sku": "sku" 
    },

    # --- 2. Опис (Descriptive Detail) ---
    "descriptions": {
        # Форма товару (Книга, Електронна книга, Аудіо).
        # Джерело: поле "book_binding_type" (ID) або "book_binding_type_label" (Текст).
        # Логіка: аналіз тексту ("М'яка", "Тверда", "Електронна").
        "product_form_source": "book_binding_type",
        
        # Назва книги (Title).
        # Джерело: "name" або "h1".
        "title_primary": "name",
        "title_fallback": "h1",
        
        # Оригінальна назва (для перекладів).
        # Джерело: "film_name_en" (історично склалося, що Yakaboo так називає це поле).
        "title_original": "film_name_en",
        
        # Автори.
        # Джерело: масив об'єктів "author_label" (містить імена).
        "contributors_author": "author", 
        
        # Перекладачі.
        # Джерело: "book_translator".
        "contributors_translator": "book_translator",
        
        # Мова тексту.
        # Джерело: "book_lang" (наприклад, "Украинский").
        "language": "book_lang",
        
        # Категорії / Тематика.
        # Джерело: масив об'єктів "category" (бажано) або масив ID "category_ids".
        "subjects_rich": "category",
        "subjects_ids": "category_ids",
        
        # Аудиторія (Вік).
        # Джерело: "age".
        "audience_age": "age",
        
        # Кількість сторінок.
        # Джерело: "book_page_count".
        "extent_pages": "book_page_count",
        
        # Розміри (Висота x Ширина).
        # Джерело: "book_binding" (наприклад, "145х200 мм").
        "measure_dimensions": "book_binding"
    },

    # --- 3. Тексти та Медіа (Collateral Detail) ---
    "collateral": {
        # Основний опис (Анотація).
        # Джерело: "description" (містить HTML).
        "description_main": "description",
        
        # Зображення обкладинки.
        # Джерело: "image".
        "cover_image": "image"
    },

    # --- 4. Видавництво (Publishing Detail) ---
    "publishing": {
        # Назва видавництва.
        # Джерело: "book_publisher".
        "publisher_name": "book_publisher",
        
        # Рік видання.
        # Джерело: "book_year".
        "publishing_year": "book_year"
    },

    # --- 5. Пов'язані товари (Related Material) ---
    "related": {
        # Інші формати цієї книги (електронна, паперова).
        # Джерело: "another_formats".
        "alternative_formats": "another_formats"
    },

    # --- 6. Ціна та Наявність (Supply Detail) ---
    "supply": {
        # Поточна ціна.
        "price": "price",
        
        # Стара ціна (для знижок).
        "old_price": "old_price",
        
        # Прапорець наявності (true/false).
        "in_stock": "is_in_stock"
    }
}
