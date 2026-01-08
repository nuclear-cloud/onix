# Copilot Instructions (Total Harvester)

## Big Picture
- **CLI-first web crawler** for book metadata extraction from Ukrainian bookstores.
- **Two-phase discovery**: Sitemap "Vacuum" + Recursive BFS "Bloodhound".
- **Distributed workers**: PostgreSQL `SKIP LOCKED` for zero-conflict parallelism.
- **Self-healing scraping**: LLM fallback when CSS selectors break.

## Key Entry Points

| File | Purpose |
|------|---------|
| `run_spider.py` | 🕷️ Main autonomous crawler (884 lines) |
| `manage.py` | 🎮 CLI management (typer + rich) |
| `scripts/seed_configs.py` | Initialize domain configurations |

## Critical Commands

```bash
# Start crawler (production: use tmux/screen)
python run_spider.py -w spider-01 -c 15

# Check status
python manage.py status

# Real-time TUI monitor
python manage.py monitor

# Add new domain
python manage.py add https://example.ua

# Clear stale locks
python manage.py flush

# Retry failed URLs
python manage.py reset-errors
```

## Required Environment

```bash
# .env file (required)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Optional LLM config
OLLAMA_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
```

## Database Schema

- `scraper_configs` — Domain configurations with `SKIP LOCKED` locking
- `product_links` — Discovered URLs (status: discovered/scraped/error)
- `product_sources` — Raw scraped data per (isbn13, domain)
- `products` — Merged "golden record" with ONIX JSON

## Scraping Architecture

### ScraperFactory (DB-driven only)
```python
# All scraping goes through factory
scraper = await ScraperFactory.get_scraper(url, db)
```
- Factory queries `ScraperConfig` for domain
- Custom providers in `app/scraper/providers/{module}/scraper.py`
- Default: `UniversalProvider` with config selectors
- **No hardcoded `if domain == ...`** outside factory

### UniversalProvider Extraction Order
1. JSON-LD structured data (`<script type="application/ld+json">`)
2. Next.js / Nuxt.js hydration (`__NEXT_DATA__`, `__NUXT__`)
3. CSS selectors from `ScraperConfig.selectors`
4. **LLM fallback** via Ollama (self-healing)

## MDM Merge Rules

`ProductMerger.DOMAIN_PRIORITY` (lower = more trusted):
```python
PRIORITY = {
    "vivat.com.ua": 1,   # Publisher
    "yakaboo.ua": 2,
    "book-ye.com.ua": 3,
    # ...
}
```

| Field | Strategy |
|-------|----------|
| Title/Form/Language | Highest-priority source |
| Description | Longest wins |
| Images | Union, sorted by priority |

Provenance stored in `Product.onix_json["extra"]["source_contributions"]`.

## DB Code Rules

- **Async SQLAlchemy 2.x** throughout (`AsyncSession`)
- If mutating `Product.onix_json`, call `flag_modified(product, "onix_json")`
- Use PostgreSQL upserts where established:
  - `ProductSource`: ON CONFLICT on `(isbn13, domain)`
  - `ProductLink`: ON CONFLICT DO NOTHING on `url`

## Config Seeding

`scripts/seed_configs.py` **must not overwrite** configs with `is_dirty=True`.

## Testing

```bash
pytest -v
```
- Tests use fixtures/mocks (no network)
- Sample HTML in `tests/test_scraper.py`
- All scraping through `ScraperFactory`

## Project Structure

```
onix_project/
├── run_spider.py          # Main crawler
├── manage.py              # CLI interface
├── requirements.txt       # Minimal deps (13 packages)
│
├── app/
│   ├── core/              # Database, config
│   ├── models/            # SQLAlchemy models
│   ├── scraper/           # Extraction logic
│   │   ├── factory.py
│   │   └── core/
│   │       └── universal_provider.py
│   └── services/          # Business logic
│       ├── product_merger.py
│       └── discovery_service.py
│
├── scripts/
│   └── seed_configs.py
│
└── tests/
```

## When Changing Code

1. **Models**: Use async SQLAlchemy patterns, `flag_modified` for JSONB
2. **Scraping**: Go through `ScraperFactory`, extend `UniversalProvider`
3. **CLI**: Use typer + rich, keep commands in `manage.py`
4. **Tests**: No network calls, use fixtures
