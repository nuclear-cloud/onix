"""
Parsers for Yakaboo to ONIX Transformation

Функції для парсингу різних секцій ONIX структури з Yakaboo даних.
"""

from typing import Any, Dict, List, Optional

from app.scraper.yakaboo.helpers import (
    extract_label_value,
    to_list,
    parse_dimensions,
    normalize_string,
    safe_int,
    safe_float,
)
from app.scraper.yakaboo.mapper import (
    AGE_TO_ONIX,
)


def parse_contributors(data: dict) -> List[Dict]:
    """
    Парсить авторів, перекладачів, редакторів, ілюстраторів.
    
    Оптимізована версія з покращеною обробкою списків.
    Якщо автор не знайдений - використовує видавництво як corporate author.
    
    Args:
        data: Raw Yakaboo data
        
    Returns:
        Список contributors з ролями та іменами
    """
    contributors = []
    has_author = False
    
    # Authors (A01) - пріоритет author_label (об'єкти з іменами)
    author_labels = data.get("author_label")
    # Оптимізація: одна перевірка замість множинних
    if author_labels:
        try:
            # Якщо є author_label - беремо імена з label
            for i, author_obj in enumerate(author_labels):
                author_name = author_obj.get("label") if isinstance(author_obj, dict) else None
                if author_name:
                    contributors.append({
                        "role": "A01",
                        "sequence": i + 1,
                        "name": normalize_string(author_name),
                    })
                    has_author = True
        except (TypeError, AttributeError):
            # Fallback якщо author_label не список
            pass
    
    # Fallback на author (ID або рядки) якщо не знайшли в author_label
    if not has_author:
        authors = to_list(data.get("author"))
        for i, author in enumerate(authors):
            if author:
                # Пропускаємо числові ID
                author_str = str(author)
                if not author_str.isdigit():
                    contributors.append({
                        "role": "A01",
                        "sequence": i + 1,
                        "name": normalize_string(author_str),
                    })
                    has_author = True
    
    # Helper функція для обробки contributors з label або fallback
    def _add_contributors(role: str, label_field: str, fallback_field: str):
        """Допоміжна функція для додавання contributors."""
        label_data = data.get(label_field)
        if label_data:
            try:
                for item in label_data:
                    name = item.get("label") if isinstance(item, dict) else None
                    if name:
                        contributors.append({
                            "role": role,
                            "name": normalize_string(name),
                        })
                return  # Якщо знайшли в label - не використовуємо fallback
            except (TypeError, AttributeError):
                pass
        
        # Fallback
        fallback_data = to_list(data.get(fallback_field))
        for item in fallback_data:
            if item:
                # Пропускаємо числові ID
                item_str = str(item)
                if not item_str.isdigit():
                    contributors.append({
                        "role": role,
                        "name": normalize_string(item_str),
                    })
    
    # Translators (B06)
    _add_contributors("B06", "book_translator_label", "book_translator")
    
    # Editors (B01)
    _add_contributors("B01", "book_editor_label", "book_editor")
    
    # Illustrators (A12)
    _add_contributors("A12", "book_painter_label", "book_painter")
    
    # Автор-складач (book_author_former_label - 0.0%)
    author_former_raw = extract_label_value(data, "book_author_former")
    if author_former_raw:
        contributors.append({
            "role": "Z99",  # Compiler (proprietary code)
            "name": normalize_string(author_former_raw),
        })
    
    # Якщо все ще немає авторів - використовуємо видавництво як corporate author
    if not has_author and not contributors:
        publisher_label = data.get("book_publisher_label")
        if publisher_label and isinstance(publisher_label, list) and len(publisher_label) > 0:
            pub_obj = publisher_label[0]
            pub_name = pub_obj.get("label") if isinstance(pub_obj, dict) else None
            if pub_name:
                contributors.append({
                    "role": "B11",  # Research by (as corporate contributor)
                    "name": normalize_string(pub_name),
                    "corporate": True,
                })
    
    return contributors


def parse_text_content(data: dict) -> List[Dict]:
    """
    Парсить описи, цитати, ключові слова, відгуки.
    
    Args:
        data: Raw Yakaboo data
        
    Returns:
        Список text_content елементів
    """
    content = []
    
    # Long description (03)
    desc = data.get("description")
    if desc:
        content.append({"type": "03", "text": normalize_string(desc)})
    
    # Short description (02)
    short = data.get("short_description")
    if short:
        content.append({"type": "02", "text": normalize_string(short)})
    
    # Quote/Review (10)
    quote = data.get("quote")
    if quote:
        content.append({"type": "10", "text": normalize_string(quote)})
    
    # Keywords (04 - Table of contents as workaround)
    keywords = data.get("keywords")
    if keywords:
        content.append({"type": "04", "text": normalize_string(keywords)})
    
    # Відгуки/Рейтинг (reviews - 2.6%)
    reviews = data.get("reviews")
    if reviews and isinstance(reviews, dict):
        reviews_count = reviews.get("reviews_count")
        rating_summary = reviews.get("rating_summary")
        if reviews_count or rating_summary:
            if reviews_count and rating_summary:
                review_text = f"Reviews: {reviews_count}, Rating: {rating_summary}"
            elif reviews_count:
                review_text = f"Reviews: {reviews_count}"
            else:
                review_text = f"Rating: {rating_summary}"
            content.append({"type": "Z99", "text": review_text})  # Review (proprietary)
    
    return content


def parse_prices(data: dict) -> List[Dict]:
    """
    Парсить всі поля цін.
    
    Args:
        data: Raw Yakaboo data
        
    Returns:
        Список price елементів
    """
    prices = []
    
    # Regular price (02 = RRP incl tax)
    regular = data.get("original_price") or data.get("regular_price") or data.get("price")
    if regular:
        prices.append({
            "type": "02",
            "amount": safe_float(regular),
            "currency": "UAH",
            "tax_included": True,
        })
    
    # Final/Special price (42 = Promotional)
    final = data.get("final_price") or data.get("special_price")
    if final and regular and safe_float(final) < safe_float(regular):
        price_entry = {
            "type": "42",
            "amount": safe_float(final),
            "currency": "UAH",
            "tax_included": True,
        }
        
        discount = data.get("discount_percent")
        if discount:
            price_entry["discount_percent"] = safe_float(discount)
        
        valid_from = data.get("special_from_date")
        if valid_from:
            price_entry["valid_from"] = str(valid_from)
        
        prices.append(price_entry)
    
    return prices


def parse_supporting_resources(data: dict) -> List[Dict]:
    """
    Парсить зображення та медіа.
    
    Оптимізована версія з покращеною обробкою списків.
    
    Args:
        data: Raw Yakaboo data
        
    Returns:
        Список supporting_resources елементів
    """
    resources = []
    seen_links = set()
    
    # Helper функція для додавання ресурсу
    def _add_resource(link: Any, resource_type: str = "01", role: Optional[str] = None):
        """Додає ресурс якщо він ще не доданий."""
        if not link:
            return
        link_str = str(link)
        if link_str not in seen_links:
            resource = {
                "type": resource_type,
                "mode": "03",
                "link": link_str,
            }
            if role:
                resource["role"] = role
            resources.append(resource)
            seen_links.add(link_str)
    
    # Main image (01 = Front cover, 03 = Image)
    _add_resource(data.get("image"), "01")
    
    # Thumbnail
    thumb = data.get("thumbnail")
    if thumb:
        _add_resource(thumb, "01", "thumbnail")
    
    # Small image
    small = data.get("small_image")
    if small:
        _add_resource(small, "01", "small")
    
    # Media gallery (старий формат)
    gallery = data.get("media_gallery")
    if gallery:
        try:
            for item in gallery:
                link = item.get("image") or item.get("url") if isinstance(item, dict) else item
                _add_resource(link, "04")
        except (TypeError, AttributeError):
            pass
    
    # Mediagallery_image (новий формат з повними URL)
    mediagallery = data.get("mediagallery_image")
    if mediagallery:
        try:
            for item in mediagallery:
                if isinstance(item, dict):
                    # Пріоритет image_url (повний URL), потім file
                    link = item.get("image_url") or item.get("file")
                else:
                    link = item
                _add_resource(link, "04")
        except (TypeError, AttributeError):
            pass
    
    return resources


def parse_supply(data: dict) -> Dict:
    """
    Парсить наявність/склад з датою доставки та регіоном.
    
    Args:
        data: Raw Yakaboo data
        
    Returns:
        Словник supply_detail
    """
    stock = data.get("stock") or []
    
    # Stock може бути масивом об'єктів або одним об'єктом
    total_qty = 0
    is_in_stock = False
    shipping_date = None
    is_europe = None
    
    if isinstance(stock, list) and len(stock) > 0:
        # Якщо це масив - беремо перший елемент або сумуємо всі
        for stock_item in stock:
            if isinstance(stock_item, dict):
                item_qty = stock_item.get("qty", 0)
                item_in_stock = stock_item.get("is_in_stock", False)
                if item_qty:
                    total_qty += safe_int(item_qty)
                if item_in_stock:
                    is_in_stock = True
                # Дата доставки (79% наявності)
                if not shipping_date:
                    shipping_date = stock_item.get("shipping_date")
                # Регіон доставки (72.2% наявності)
                if is_europe is None:
                    is_europe = stock_item.get("is_europe")
        # Якщо не знайшли в масиві - беремо перший елемент
        if total_qty == 0 and len(stock) > 0:
            first_item = stock[0]
            if isinstance(first_item, dict):
                total_qty = safe_int(first_item.get("qty", 0))
                is_in_stock = first_item.get("is_in_stock", False)
                if not shipping_date:
                    shipping_date = first_item.get("shipping_date")
                if is_europe is None:
                    is_europe = first_item.get("is_europe")
    elif isinstance(stock, dict):
        # Якщо це один об'єкт
        total_qty = safe_int(stock.get("qty", 0))
        is_in_stock = stock.get("is_in_stock", False)
        shipping_date = stock.get("shipping_date")
        is_europe = stock.get("is_europe")
    else:
        # Fallback
        is_in_stock = bool(stock)
    
    supply_detail = {
        "supplier": "Yakaboo",
        "availability": "21" if is_in_stock else "40",  # 21=In stock, 40=Not available
        "quantity": total_qty if total_qty > 0 else None,
    }
    
    # Дата доставки
    if shipping_date:
        supply_detail["availability_date"] = str(shipping_date)[:10]
    
    # Регіон доставки
    if is_europe is not None:
        supply_detail["territory"] = "EU" if is_europe else "UA"
    
    return supply_detail


def parse_subjects_extended(data: dict) -> List[Dict]:
    """
    Розширена обробка subjects з усіх тематичних полів.
    
    Args:
        data: Raw Yakaboo data
        
    Returns:
        Список subject елементів
    """
    subjects = []
    
    # Категорії (базові)
    categories = data.get("category") or []
    for cat in to_list(categories):
        if isinstance(cat, dict):
            cat_id = cat.get("category_id") or cat.get("id")
            cat_name = cat.get("name")
        else:
            cat_id = None
            cat_name = str(cat)
        
        if cat_name:
            subjects.append({
                "scheme": "24",  # Proprietary
                "code": str(cat_id) if cat_id else None,
                "text": normalize_string(cat_name),
            })
    
    # Період літератури (3.8%)
    period = extract_label_value(data, "book_period")
    if period:
        subjects.append({"scheme": "24", "code": "period", "text": normalize_string(period)})
    
    # Тип літератури (0.2%)
    literature = extract_label_value(data, "book_literature")
    if literature:
        subjects.append({"scheme": "24", "code": "literature_type", "text": normalize_string(literature)})
    
    # Тип видання (0.1%)
    book_type = extract_label_value(data, "book_type")
    if book_type:
        subjects.append({"scheme": "24", "code": "edition_type", "text": normalize_string(book_type)})
    
    # Справочні видання (0.3%)
    reference = extract_label_value(data, "book_reference")
    if reference:
        subjects.append({"scheme": "24", "code": "reference", "text": normalize_string(reference)})
    
    # Історичний період (0.4%)
    history = extract_label_value(data, "book_history")
    if history:
        subjects.append({"scheme": "24", "code": "history_period", "text": normalize_string(history)})
    
    return subjects


def parse_measures_extended(data: dict) -> List[Dict]:
    """
    Розширена обробка measures з розмірами та вагою.
    
    Args:
        data: Raw Yakaboo data
        
    Returns:
        Список measure елементів
    """
    measures = []
    
    # Вага (67.4%)
    weight_raw = extract_label_value(data, "book_weight")
    if weight_raw:
        w = safe_float(weight_raw)
        if w > 0:
            measures.append({"type": "08", "value": w, "unit": "gr"})
    
    # Розміри з формату (89.1%)
    binding_label_raw = extract_label_value(data, "book_binding")
    if binding_label_raw:
        binding_label_str = str(binding_label_raw)
        dims = parse_dimensions(binding_label_str)
        if dims["height"]:
            measures.append({"type": "01", "value": dims["height"], "unit": "mm"})
        if dims["width"]:
            measures.append({"type": "02", "value": dims["width"], "unit": "mm"})
        if dims["thickness"]:
            measures.append({"type": "03", "value": dims["thickness"], "unit": "mm"})
    
    return measures


def parse_audience_extended(data: dict) -> List[Dict]:
    """
    Розширена обробка audience з віком та класом.
    
    Args:
        data: Raw Yakaboo data
        
    Returns:
        Список audience елементів
    """
    audience = []
    
    # Вік читача (10.7%)
    age_label = extract_label_value(data, "age")
    if age_label:
        age_text = str(age_label).lower()
        age_value = AGE_TO_ONIX.get(age_text, age_text)
        audience.append({"type": "01", "value": age_value})
    
    # Клас (1.5%)
    book_class = extract_label_value(data, "book_class")
    if book_class:
        audience.append({"type": "XX", "value": normalize_string(book_class)})  # Educational level
    
    return audience


def parse_publishing_dates(data: dict) -> List[Dict]:
    """
    Парсить дати публікації.
    
    Args:
        data: Raw Yakaboo data
        
    Returns:
        Список publishing_date елементів
    """
    dates = []
    
    # Publication year (01) - використовуємо extract_label_value
    year_raw = extract_label_value(data, "book_year")
    if year_raw:
        dates.append({"role": "01", "date": normalize_string(year_raw)})
    
    # First publication (11)
    first_raw = extract_label_value(data, "book_first_year")
    if first_raw:
        dates.append({"role": "11", "date": normalize_string(first_raw)})
    
    # In stores date (09)
    published = data.get("published_at")
    if published:
        dates.append({"role": "09", "date": str(published)[:10]})
    
    # Дата доставки з stock[0].shipping_date (79% наявності)
    stock = data.get("stock") or []
    if isinstance(stock, list) and len(stock) > 0:
        first_stock = stock[0]
        if isinstance(first_stock, dict):
            shipping_date = first_stock.get("shipping_date")
            if shipping_date:
                dates.append({"role": "09", "date": str(shipping_date)[:10]})
    
    return dates


