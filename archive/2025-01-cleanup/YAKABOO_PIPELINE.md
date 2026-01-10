# Yakaboo Pipeline - Quick Start Guide

## 📁 Project Structure

```
onix_project/
├── app/
│   ├── adapters/            # 🔌 Data source adapters
│   │   ├── base.py          # Base adapter interface
│   │   └── yakaboo.py       # Yakaboo adapter
│   │
│   ├── config/              # ⚙️ Configuration
│   │   └── thema_map.py     # Genre → THEMA mapping
│   │
│   ├── services/            # 🏭 Business logic
│   │   └── product_service.py  # Product management (2 modes)
│   │
│   ├── schemas/             # 📦 DTOs
│   │   ├── product_full.py     # Full product DTO
│   │   └── product_market.py   # Market data DTO
│   │
│   ├── models/              # 🗄️ Database models
│   │   └── product.py
│   │
│   └── utils/               # 🛠️ Tools
│       └── mapper.py        # Universal JSON mapper
│
└── scripts/                 # 🚀 Entry points
    ├── daily_import.py      # PATH 1: Full catalog import
    ├── hourly_sync.py       # PATH 2: Fast market sync
    └── demo_pipeline.py     # Demo with test data
```

## 🎯 Two Operation Modes

### PATH 1: Full Catalog Import (Daily)
**When:** Once per day (night)  
**What:** Complete product data (descriptions, images, specs)  
**Speed:** ~100 products/batch  
**Creates:** New products + updates existing

```bash
# Run full import
python scripts/daily_import.py --file data/yakaboo_complete_final.jsonl --limit 100

# With custom batch size
python scripts/daily_import.py --file products.json --batch-size 50
```

### PATH 2: Market Sync (Hourly)
**When:** Every hour  
**What:** Only prices and availability  
**Speed:** ~500 products/batch (5x faster)  
**Creates:** Nothing (only updates existing)

```bash
# Run market sync
python scripts/hourly_sync.py --file data/yakaboo_prices.json --limit 1000

# With larger batch
python scripts/hourly_sync.py --file prices.json --batch-size 1000
```

## 🧪 Quick Test

```bash
# Activate venv
source venv/bin/activate

# Run demo with test data
python scripts/demo_pipeline.py
```

This will:
1. ✅ Import 2 test products (full mode)
2. ⚡ Update their prices (market mode)
3. 📊 Show statistics

## 📊 Expected Output

```
============================================================
🌅 DEMO: FULL IMPORT MODE
============================================================
✅ Created: Дюна (978-0441172719)
✅ Created: Кобзар (978-9660123456)

📈 IMPORT RESULTS
✅ Created: 2
🔄 Updated: 0
============================================================

⚡ DEMO: MARKET SYNC MODE
============================================================
✅ Market updated: 978-0441172719
✅ Market updated: 978-9660123456

📈 SYNC RESULTS
🔄 Updated: 2
⏱️  Duration: 0.15s
⚡ Speed: 13.3 products/second
============================================================
```

## 🏗️ Architecture Components

### 1. **Adapters** (`app/adapters/`)
- `BaseAdapter` - Abstract interface
- `YakabooAdapter` - Yakaboo implementation
- Methods: `parse_full()`, `parse_market()`, `validate()`

### 2. **Schemas** (`app/schemas/`)
- `ProductFullDTO` - Complete product (30+ fields)
- `ProductMarketDTO` - Market data only (5 fields)
- Pydantic validation included

### 3. **Service** (`app/services/product_service.py`)
- `import_full_batch()` - PATH 1 logic
- `update_market_batch()` - PATH 2 logic
- Database operations

### 4. **Scripts** (`scripts/`)
- `daily_import.py` - Full import CLI
- `hourly_sync.py` - Market sync CLI
- `demo_pipeline.py` - Test with fake data

## 🔧 Configuration

### THEMA Mapping (`app/config/thema_map.py`)
```python
CATEGORY_TO_THEMA = {
    "Фантастика": "FBA",
    "Детективи": "FF",
    # ... 60+ categories
}
```

### Database (`app/models/product.py`)
- Uses existing `Product` model
- Fields: isbn13, title, author, price, etc.

## 📝 Usage Examples

### Full Import from File
```python
from app.adapters.yakaboo import YakabooAdapter
from app.services.product_service import ProductService

adapter = YakabooAdapter()
service = ProductService(db_session)

# Load data
with open('products.json') as f:
    data = json.load(f)

# Import
stats = await service.import_full_batch(data, adapter)
print(f"Created: {stats['created']}, Updated: {stats['updated']}")
```

### Market Sync
```python
# Fast update (only prices)
result = await service.update_market_batch(market_data, adapter)
print(f"Updated {result.updated} in {result.duration_seconds}s")
```

## 🚀 Production Deployment

### Cron Jobs
```bash
# Daily full import (3 AM)
0 3 * * * cd /home/ubuntu/onix_project && source venv/bin/activate && python scripts/daily_import.py

# Hourly market sync
0 * * * * cd /home/ubuntu/onix_project && source venv/bin/activate && python scripts/hourly_sync.py
```

### Docker (optional)
```bash
docker-compose up -d
docker-compose exec app python scripts/daily_import.py
```

## ⚠️ Important Notes

1. **Market Sync** does NOT create new products - only updates existing
2. **Full Import** is slow but complete - use once per day
3. **ISBN-13** is the main key for matching products
4. **Batch sizes**: 100 for full, 500+ for market
5. **Validation** happens automatically in adapters

## 🐛 Troubleshooting

### "Product not found" in market sync
✅ Normal - product wasn't imported yet. Run full import first.

### "Invalid ISBN-13"
✅ Check that ISBN has 13 digits (remove dashes if needed)

### Slow performance
✅ Increase `--batch-size` or use market mode for updates

## 📚 Next Steps

1. ✅ Test with demo: `python scripts/demo_pipeline.py`
2. ✅ Run with real data: `python scripts/daily_import.py --file your_data.json`
3. ✅ Set up cron jobs for automation
4. 🔜 Add more adapters (KSD, Vivat, Book-Ye)
5. 🔜 Implement real API clients

## 🎉 Done!

The complete Yakaboo pipeline is ready to use! 🚀
