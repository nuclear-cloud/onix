# Yakaboo Import Mapping System

## Quick Start

```bash
# Run with venv helper script (easiest)
./scripts/run_yakaboo_import.sh --limit 20 --verbose

# Or manually with venv
source .venv/bin/activate
export DATABASE_URL=postgresql://onix_user:onix_secure_pass_2024@localhost:5432/onix_db
python scripts/import_yakaboo_prisma.py --limit 100
```

## How It Works

### 1. Configuration File (`app/config/yakaboo_mappings.py`)

All mappings live here. Structure:

```python
YAKABOO_TO_CATALOG = {
    'target_field': {
        'source_fields': ['yakaboo_field'],  # Where to look
        'transform': transform_function,      # How to convert
        'required': True/False,              # Must have value?
        'description': 'What this is',       # Documentation
    }
}
```

### 2. Named Transforms

Reusable functions that know how to extract and convert data:

- `extract_isbn13()` - Gets clean 13-digit ISBN from multiple possible fields
- `map_language_code()` - Converts Yakaboo language IDs (332272) to ISO codes (ukr)
- `map_product_form()` - Converts binding types to ONIX codes (BB=hardback, BC=paperback)
- `extract_first_label()` - Pulls value from Yakaboo label arrays
- `extract_publication_year()` - Creates date from year field
- And more...

### 3. Mapper Service (`app/services/mapper.py`)

The engine that applies mappings:

```python
from app.services.mapper import UniversalMapper
from app.config.yakaboo_mappings import YAKABOO_TO_CATALOG

mapper = UniversalMapper(YAKABOO_TO_CATALOG)
catalog_data = mapper.apply(raw_yakaboo_json)
```

## Current Mappings

### Main Product Fields (YAKABOO_TO_CATALOG)

| Target Field | Source Field(s) | Transform | Required |
|-------------|-----------------|-----------|----------|
| `isbn13` | `book_isbn`, `book_isbn_label` | `extract_isbn13` | ✅ Yes |
| `title` | `name` | Direct | ✅ Yes |
| `subtitle` | `short_description` | Direct | No |
| `language_code` | `book_lang` | `map_language_code` | ✅ Yes |
| `publisher_name` | `book_publisher_label` | `extract_first_label` | No |
| `product_form_code` | `book_binding_label` | `map_product_form` | ✅ Yes |
| `page_count` | `book_page_count` | `extract_page_count` | No |
| `publication_date` | `book_publication_year` | `extract_publication_year` | No |

### Related Data (Future)

- `YAKABOO_TO_CONTRIBUTOR` - Author/translator mappings
- `YAKABOO_TO_TEXT_CONTENT` - Descriptions
- `YAKABOO_TO_MEDIA_FILE` - Cover images
- `YAKABOO_TO_PRICE` - Pricing data

## Adding New Mappings

### Step 1: Add Transform Function (if needed)

```python
# In app/config/yakaboo_mappings.py

def extract_series_title(raw: Dict[str, Any]) -> Optional[str]:
    """Extract book series name."""
    return raw.get('book_series')
```

### Step 2: Add to Mapping Dict

```python
YAKABOO_TO_CATALOG = {
    # ... existing mappings ...
    
    'collection_title': {
        'source_fields': ['book_series'],
        'transform': extract_series_title,
        'required': False,
        'description': 'Book series name',
    },
}
```

### Step 3: Test

```bash
./scripts/run_yakaboo_import.sh --limit 5 --verbose
```

## ONIX Code Reference

### Product Form Codes
- `BB` - Hardback (твердий палітурка)
- `BC` - Paperback (м'яка палітурка)
- `DG` - Digital download

### Publishing Status
- `04` - Active (в продажу)
- `02` - Forthcoming (очікується)

### Language Codes (ISO 639-2)
- `ukr` - Ukrainian
- `rus` - Russian
- `eng` - English

### Contributor Roles
- `A01` - Author (автор)
- `B06` - Translator (перекладач)
- `A12` - Illustrator (ілюстратор)

## Troubleshooting

### Issue: Wrong language detected

Check `book_lang` in raw data:
```bash
head -1 data/yakaboo_complete_final.jsonl | python3 -m json.tool | grep book_lang
```

Update mapping in `map_language_code()` if needed.

### Issue: Missing publisher

Publisher comes from `book_publisher_label[0].label`. Verify field exists:
```bash
head -1 data/yakaboo_complete_final.jsonl | python3 -m json.tool | grep -A5 book_publisher
```

### Issue: Import fails with database error

Check Prisma schema matches table:
```bash
prisma generate
psql $DATABASE_URL -c "\d catalog_products"
```

## File Structure

```
app/
├── config/
│   └── yakaboo_mappings.py    ← All mapping config HERE
├── services/
│   └── mapper.py               ← Universal mapper engine
scripts/
├── import_yakaboo_prisma.py    ← Main import script
└── run_yakaboo_import.sh       ← Helper (with venv)
```

## Next Steps

1. ✅ Basic catalog fields working
2. 🔜 Add contributor (author) import
3. 🔜 Add text_content (descriptions) import
4. 🔜 Add media_file (cover images) import
5. 🔜 Add price tracking
