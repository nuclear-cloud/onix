"""
Yakaboo Field Mappings Configuration
=====================================

Clear mapping from Yakaboo native JSON format to our normalized catalog schema.

Structure:
    source_field → transform_function → target_field

All transforms are named and reusable.
"""
from typing import Any, Optional, List, Dict
from datetime import datetime


# ============================================================================
# NAMED TRANSFORMS (Reusable Functions)
# ============================================================================

def extract_isbn13(raw: Dict[str, Any]) -> Optional[str]:
    """
    Extract and validate ISBN-13 from Yakaboo data.
    
    Tries:
    1. Direct field: book_isbn
    2. Label array: book_isbn_label[0].label
    
    Returns: Clean 13-digit ISBN or None
    """
    # Method 1: Direct field
    if 'book_isbn' in raw:
        isbn = raw['book_isbn']
        if isinstance(isbn, str) and isbn.strip():
            clean = isbn.replace('-', '').replace(' ', '')
            if len(clean) == 13 and clean.isdigit():
                return clean
    
    # Method 2: Label array
    if 'book_isbn_label' in raw:
        labels = raw['book_isbn_label']
        if isinstance(labels, list) and labels:
            for label_obj in labels:
                if isinstance(label_obj, dict):
                    isbn = label_obj.get('label', '')
                    if isbn and isinstance(isbn, str):
                        clean = isbn.replace('-', '').replace(' ', '')
                        if len(clean) == 13 and clean.isdigit():
                            return clean
    
    return None


def extract_first_label(raw: Dict[str, Any], field_name: str) -> Optional[str]:
    """
    Extract first value from Yakaboo label array.
    
    Example:
        book_publisher_label: [{"label": "Vivat"}] → "Vivat"
    """
    labels = raw.get(field_name, [])
    if isinstance(labels, list) and labels:
        label_obj = labels[0]
        if isinstance(label_obj, dict):
            return label_obj.get('label')
    return None


def map_language_code(raw_code: Any) -> str:
    """
    Map Yakaboo language ID to ISO 639-2 code.
    
    Yakaboo uses numeric IDs in an array:
        [332272] → ukr (Ukrainian)
        [332273] → rus (Russian)
        [332271] → eng (English - old code)
        [332987] → eng (English - new code)
    
    Default: ukr
    """
    if not raw_code:
        return 'ukr'
    
    # Handle array format [332272] or single value 332272
    if isinstance(raw_code, list) and raw_code:
        raw_code = raw_code[0]
    
    code_map = {
        # String keys
        '332272': 'ukr',
        '332273': 'rus',
        '332271': 'eng',
        '332987': 'eng',  # English (main code in Yakaboo)
        # Integer keys
        332272: 'ukr',
        332273: 'rus',
        332271: 'eng',
        332987: 'eng',
    }
    
    return code_map.get(raw_code, code_map.get(str(raw_code), 'ukr'))


def map_product_form(raw: Dict[str, Any]) -> str:
    """
    Map Yakaboo binding type to ONIX ProductForm code.
    
    ONIX Codes:
        BB = Hardback
        BC = Paperback
        BL = Loose-leaf
        DG = Digital download and online
    
    Default: BB (book)
    """
    binding = extract_first_label(raw, 'book_binding_label')
    if not binding:
        return 'BB'
    
    binding_lower = binding.lower()
    
    if 'тверд' in binding_lower or 'hard' in binding_lower:
        return 'BB'  # Hardback
    elif 'м\'як' in binding_lower or 'paper' in binding_lower or 'soft' in binding_lower:
        return 'BC'  # Paperback
    else:
        return 'BB'  # Default to hardback


def extract_publication_year(raw: Dict[str, Any]) -> Optional[datetime]:
    """
    Extract publication date from year field.
    
    Yakaboo provides: book_publication_year
    Returns: datetime object (January 1st of that year) or None
    """
    year = raw.get('book_publication_year')
    if not year:
        return None
    
    try:
        year_int = int(str(year)[:4])
        if 1800 <= year_int <= 2100:  # Sanity check
            return datetime(year_int, 1, 1)
    except (ValueError, TypeError):
        pass
    
    return None


def extract_page_count(raw: Dict[str, Any]) -> Optional[int]:
    """
    Extract page count from Yakaboo data.
    """
    pages = raw.get('book_page_count')
    if pages:
        try:
            page_int = int(pages)
            if 1 <= page_int <= 10000:  # Sanity check
                return page_int
        except (ValueError, TypeError):
            pass
    return None


def extract_price(raw: Dict[str, Any]) -> Optional[float]:
    """
    Extract current price from Yakaboo data.
    """
    price = raw.get('price')
    if price:
        try:
            return float(price)
        except (ValueError, TypeError):
            pass
    return None


def extract_old_price(raw: Dict[str, Any]) -> Optional[float]:
    """
    Extract old/original price (for discounts).
    """
    old_price = raw.get('old_price')
    if old_price:
        try:
            return float(old_price)
        except (ValueError, TypeError):
            pass
    return None


def check_in_stock(raw: Dict[str, Any]) -> bool:
    """
    Check if product is in stock.
    
    Yakaboo uses: for_filter_is_in_stock
    """
    return raw.get('for_filter_is_in_stock') != '0'


def extract_image_url(raw: Dict[str, Any]) -> Optional[str]:
    """
    Extract main product image URL.
    """
    image = raw.get('image')
    if image and isinstance(image, str):
        # Ensure it's a full URL
        if image.startswith('http'):
            return image
        elif image.startswith('/'):
            return f"https://yakaboo.ua{image}"
    return None


def extract_product_url(raw: Dict[str, Any]) -> Optional[str]:
    """
    Build product URL from url_key.
    """
    url_key = raw.get('url_key')
    if url_key:
        return f"https://yakaboo.ua/{url_key}"
    return None


def clean_description(raw: Dict[str, Any]) -> Optional[str]:
    """
    Extract and clean description text.
    Removes HTML tags if present.
    """
    desc = raw.get('description') or raw.get('short_description')
    if desc and isinstance(desc, str):
        # Basic HTML tag removal
        import re
        clean = re.sub(r'<[^>]+>', '', desc)
        clean = clean.strip()
        if clean:
            return clean
    return None


def is_active(raw: Dict[str, Any]) -> bool:
    """
    Check if product is active/enabled.
    """
    status = raw.get('status')
    return status != 'disabled'


# ============================================================================
# FIELD MAPPINGS
# ============================================================================

YAKABOO_TO_CATALOG = {
    # ========================================
    # IDENTIFIERS
    # ========================================
    'isbn13': {
        'source_fields': ['book_isbn', 'book_isbn_label'],
        'transform': extract_isbn13,
        'required': True,
        'description': 'Primary identifier: 13-digit ISBN'
    },
    
    'proprietary_id': {
        'source_fields': ['sku'],
        'transform': lambda raw: raw.get('sku'),
        'required': False,
        'description': 'Yakaboo internal SKU'
    },
    
    # ========================================
    # TITLE & DESCRIPTION
    # ========================================
    'title': {
        'source_fields': ['name'],
        'transform': lambda raw: raw.get('name') or 'Без назви',
        'required': True,
        'description': 'Book title'
    },
    
    'subtitle': {
        'source_fields': ['short_description'],
        'transform': lambda raw: raw.get('short_description'),
        'required': False,
        'description': 'Short description or subtitle'
    },
    
    # ========================================
    # PRODUCT CLASSIFICATION
    # ========================================
    'product_form_code': {
        'source_fields': ['book_binding_label'],
        'transform': map_product_form,
        'required': True,
        'description': 'ONIX product form (BB=hardback, BC=paperback)'
    },
    
    'publishing_status_code': {
        'source_fields': ['status'],
        'transform': lambda raw: '04',  # 04 = Active
        'required': True,
        'description': 'ONIX publishing status (04=Active)'
    },
    
    # ========================================
    # LANGUAGE
    # ========================================
    'language_code': {
        'source_fields': ['book_lang'],
        'transform': lambda raw: map_language_code(raw.get('book_lang')),
        'required': True,
        'description': 'ISO 639-2 language code (ukr, rus, eng)'
    },
    
    # ========================================
    # PUBLISHER & AUTHOR
    # ========================================
    'publisher_name': {
        'source_fields': ['book_publisher_label'],
        'transform': lambda raw: extract_first_label(raw, 'book_publisher_label'),
        'required': False,
        'description': 'Publisher name'
    },
    
    # ========================================
    # PHYSICAL DETAILS
    # ========================================
    'page_count': {
        'source_fields': ['book_page_count'],
        'transform': extract_page_count,
        'required': False,
        'description': 'Number of pages'
    },
    
    # ========================================
    # DATES
    # ========================================
    'publication_date': {
        'source_fields': ['book_publication_year'],
        'transform': extract_publication_year,
        'required': False,
        'description': 'Publication date (from year)'
    },
    
    # ========================================
    # STATUS
    # ========================================
    'is_active': {
        'source_fields': ['status'],
        'transform': is_active,
        'required': True,
        'description': 'Whether product is active'
    },
}


# ============================================================================
# RELATED DATA MAPPINGS (for future use)
# ============================================================================

YAKABOO_TO_CONTRIBUTOR = {
    'person_name': {
        'source_fields': ['author_label'],
        'transform': lambda raw: extract_first_label(raw, 'author_label'),
        'required': False,
        'description': 'Author name'
    },
    
    'role_code': {
        'source_fields': [],
        'transform': lambda raw: 'A01',  # A01 = By (author)
        'required': True,
        'description': 'ONIX contributor role'
    },
    
    'contributor_type': {
        'source_fields': [],
        'transform': lambda raw: 'P',  # P = Person
        'required': True,
        'description': 'Person or Corporate'
    },
    
    'sequence_number': {
        'source_fields': [],
        'transform': lambda raw: 1,
        'required': False,
        'description': 'Order in contributor list'
    },
}


YAKABOO_TO_TEXT_CONTENT = {
    'text_type_code': {
        'source_fields': [],
        'transform': lambda raw: '03',  # 03 = Description
        'required': True,
        'description': 'ONIX text type'
    },
    
    'content': {
        'source_fields': ['description', 'short_description'],
        'transform': clean_description,
        'required': False,
        'description': 'Description text (HTML stripped)'
    },
}


YAKABOO_TO_MEDIA_FILE = {
    'resource_content_type_code': {
        'source_fields': [],
        'transform': lambda raw: '01',  # 01 = Front cover
        'required': True,
        'description': 'ONIX resource content type'
    },
    
    'resource_mode_code': {
        'source_fields': [],
        'transform': lambda raw: '03',  # 03 = Image
        'required': True,
        'description': 'ONIX resource mode'
    },
    
    'file_link': {
        'source_fields': ['image'],
        'transform': extract_image_url,
        'required': False,
        'description': 'Image URL'
    },
}


YAKABOO_TO_PRICE = {
    'price_amount': {
        'source_fields': ['price'],
        'transform': extract_price,
        'required': False,
        'description': 'Current price'
    },
    
    'price_type_code': {
        'source_fields': [],
        'transform': lambda raw: '01',  # 01 = RRP (Recommended Retail Price)
        'required': True,
        'description': 'ONIX price type'
    },
    
    'currency_code': {
        'source_fields': [],
        'transform': lambda raw: 'UAH',
        'required': True,
        'description': 'Currency code'
    },
    
    'stock_quantity': {
        'source_fields': ['for_filter_is_in_stock'],
        'transform': lambda raw: 1 if check_in_stock(raw) else 0,
        'required': False,
        'description': 'In stock indicator'
    },
}


# ============================================================================
# MAPPING DOCUMENTATION
# ============================================================================

MAPPING_GUIDE = """
How to Use These Mappings
==========================

1. Each target field has:
   - source_fields: List of Yakaboo fields to look at
   - transform: Function to convert raw data
   - required: Whether field is mandatory
   - description: What this field represents

2. Apply mappings:
   ```python
   from app.config.yakaboo_mappings import YAKABOO_TO_CATALOG, extract_isbn13
   
   # For a single field
   isbn = extract_isbn13(yakaboo_raw_data)
   
   # For all catalog fields
   catalog_data = {}
   for target_field, config in YAKABOO_TO_CATALOG.items():
       catalog_data[target_field] = config['transform'](yakaboo_raw_data)
   ```

3. Add new mappings:
   - Define transform function at top of file
   - Add entry to appropriate mapping dict
   - Document with description

4. Field Naming Convention:
   - Source: Yakaboo's original field names (snake_case)
   - Target: Our Prisma model field names (snake_case)
   - Transforms: Descriptive function names (extract_*, map_*, check_*, clean_*)

ONIX Code Reference:
====================
- Product Form: BB (hardback), BC (paperback), DG (digital)
- Publishing Status: 04 (active), 01 (cancelled), 02 (forthcoming)
- Language: ukr, rus, eng (ISO 639-2)
- Contributor Role: A01 (author), B06 (translator), A12 (illustrator)
- Text Type: 01 (blurb), 03 (description), 04 (table of contents)
- Price Type: 01 (RRP), 02 (agency), 03 (wholesale)
"""
