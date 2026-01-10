# ONIX Project Status (January 6, 2026)

## 📋 Огляд проєкту

**ONIX Catalog для українських книжкових магазинів** - система управління метаданими книг з постійною синхронізацією з довідниками ONIX та THEMA класифікації.

### Стек технологій
- **Backend**: Python 3.12 + FastAPI
- **Database**: PostgreSQL 16.11 (native, port 5432)
- **ORM**: SQLAlchemy 2.x async
- **Data Format**: ONIX XML 3.0 + JSON

---

## ✅ Реалізовано

### 1️⃣ Довідники (Reference Data)

#### ONIX Коди (ONIX_BookProduct_Codelists_Issue_71.json)
- **Таблиця**: `ref_onix_codelists`
- **Записів**: **4,748 активних кодів**
- **Структура**: 
  - `list_number` + `code` (composite primary key)
  - `description`, `label_en`, `label_uk`
  - `is_active` (soft delete)
- **Використання**: Валідація типів продуктів, форм видання, ролей контрибьюторів

#### THEMA Класифікація (thema_v1.6_uk.json)
- **Таблиця**: `ref_thema_subjects`
- **Записів**: **9,187 активних кодів**
- **Структура**:
  - `code` (primary key) - e.g. "Y", "YF", "YFB"
  - `parent_code` (nullable self-referential FK)
  - `label_uk` (Ukrainian labels)
  - `is_active` (soft delete)
  - Index на `label_uk` для швидкого пошуку
- **Ієрархія**: 
  - Рівень 0: Корені (e.g. "Y" - Дитяча литература)
  - Рівень 1-3: Підкатегорії з FK констрейнтами

**Алгоритм завантаження**: BFS топологічний сортинг
- Гарантує: батьки завжди вставляються перед дітьми
- Вирішує: проблеми FK constraint violations у багаторівневих ієрархіях

---

### 2️⃣ Каталог книг (19 таблиць)

#### Основна таблиця: `catalog_products`
- **100 тестових записів**
- **Поля**:
  - `id` (UUID, primary key)
  - `record_reference` (unique) - ONIX identifier
  - `isbn_13` (unique index)
  - `product_form` (enum, FK to ONIX codes)
  - `publishing_status` (enum, FK to ONIX codes)
  - `is_ukrainian` (boolean)
  - `publisher_id` (FK to publishers)
  - `created_at`, `updated_at` (timestamps)

#### Деталі книги (пов'язані таблиці з cascade):

| Таблиця | Мета | Зв'язок |
|---------|------|---------|
| `catalog_titles` | Заголовки (основні, альтернативні) | 1:N |
| `catalog_publishers` | Видавництва | N:1 |
| `catalog_contributors` | Автори (normalizовані) | N:N (junction) |
| `catalog_subjects` | Категорії (THEMA, BISAC) | 1:N (FK to ref_thema) |
| `catalog_languages` | Мови | 1:N |
| `catalog_extents` | Кількість сторінок, тривалість | 1:N |
| `catalog_measures` | Розміри, вага | 1:N |
| `catalog_audience_ranges` | Вікові групи | 1:N |
| `catalog_prizes` | Премії та нагороди | 1:N |
| `catalog_text_contents` | Описи, анотації | 1:N |
| `catalog_cited_contents` | Рецензії, цитати | 1:N |
| `catalog_related_products` | Пов'язані видання (e-book, аудіо) | 1:N |
| `catalog_collections` | Серії | 1:N (junction) |
| `catalog_publishing_dates` | Дати публікації | 1:N |

#### Junction таблиці:
- `catalog_product_contributors_link` - Product ↔ Contributor (з role + sequence)
- `catalog_product_collections_link` - Product ↔ Collection (з sequence number)

---

### 3️⃣ Архітектура кодингу

```
onix_project/
├── app/
│   ├── core/
│   │   ├── config.py           # Settings (DATABASE_URL, OLLAMA_BASE_URL)
│   │   ├── database.py         # AsyncSession, SQLAlchemy setup
│   │   └── logging.py
│   ├── models/
│   │   ├── catalog.py          # 📌 ОСНОВНІ МОДЕЛІ (400+ lines)
│   │   │   ├── RefOnixCodelist
│   │   │   ├── RefThemaSubject (з иерархией)
│   │   │   ├── CatalogProduct (главная таблица)
│   │   │   ├── CatalogTitle, Publisher, Contributor
│   │   │   └── ... (18 деталізованих таблиць)
│   │   ├── codes_v71.py        # ONIX Enums (ProductForm, Status, etc.)
│   │   └── market.py
│   ├── services/
│   │   └── catalog_loader.py   # 🔄 CatalogLoader з cache TTL
│   └── schemas/
│       └── onix_full.py        # Pydantic schemas
├── scripts/
│   └── load_reference_codes.py # 📥 UPSERT loader з BFS алгоритмом
├── migrations/
│   ├── 20260106_reference_upsert.sql
│   └── reference_tables.dbml
└── tests/
    ├── test_reference_loaders.py  # ✅ BFS sorting tests
    ├── test_catalog_loader.py     # ✅ Cache TTL tests
    └── ... (9 тестів, всі passing)
```

---

### 4️⃣ Ключові особливості

#### ✨ UPSERT семантика (zero-downtime updates)
```sql
-- Замість TRUNCATE + INSERT:
INSERT INTO ref_thema_subjects (...) 
VALUES (...)
ON CONFLICT (code) 
DO UPDATE SET 
  label_uk = EXCLUDED.label_uk,
  is_active = EXCLUDED.is_active
```

#### 🌳 Soft Delete для historical integrity
- Всі коди з `is_active = FALSE` зберігаються
- Видалені коди не видаляються з БД, а позначаються неактивними
- Дозволяє відстежувати видалення та аудит

#### 🔗 Самопосилаючаяся FK для ієрархій (THEMA)
```python
parent_code = Column(String(20), ForeignKey("ref_thema_subjects.code"), nullable=True)
children = relationship("RefThemaSubject", backref=backref("parent", remote_side=[code]))
```

#### 🎯 Composite Primary Key для ONIX кодів
```python
list_number = Column(Integer, primary_key=True)
code = Column(String(50), primary_key=True)
```
Гарантує унікальність в межах списку

#### 📦 Batch Processing (1000 записів на batch)
- Обходить PostgreSQL parameter limit (~65,535)
- Зменшує мережеві затримки
- Використовується у loader скрипті

#### 🧠 BFS топологічний сортинг для THEMA
```python
# Розв'язує проблему: дити вставляються до батьків (FK violation)
# Рішення: BFS від roots, групування по levels, вставка level-by-level
for level in sorted(records_by_level.keys()):
    # Усі батьки рівня N гарантовано вставлені перед дітьми рівня N+1
```

#### ⏰ Cache TTL (1 година) для довідників
- `CatalogLoader.cache_ttl_seconds = 3600`
- Метод `refresh_thema_cache()` для примусового оновлення
- Фільтрує тільки `is_active=TRUE` записи

---

## 📊 Статистика БД

```
╔═══════════════════╦═════════╦═════════╗
║ Таблиця           ║ Записів ║ Активні ║
╠═══════════════════╬═════════╬═════════╣
║ ref_onix_codes    ║  4,748  ║  4,748  ║
║ ref_thema_codes   ║  9,187  ║  9,187  ║
║ catalog_products  ║    100  ║    100  ║
║ catalog_titles    ║    100  ║    100  ║
╚═══════════════════╩═════════╩═════════╝

Всього таблиць: 21
Тесто passed: 9/9 ✅
```

---

## 🧪 Тести (9 passing)

```bash
tests/test_reference_loaders.py
  ✅ test_load_onix_codelists_structure - UPSERT параметри
  ✅ test_load_thema_uses_bfs_topological_sort - BFS алгоритм

tests/test_catalog_loader.py
  ✅ test_catalog_loader_instantiation
  ✅ test_market_loader_instantiation

tests/test_catalog_loader_validation.py
  ✅ test_process_subjects_skips_invalid_thema
  ✅ test_process_subjects_allows_non_thema

tests/test_market_loader.py
  ✅ test_market_loader_update_price

tests/test_thema_cache.py
  ✅ test_ensure_thema_cache_loads_once
  ✅ test_thema_cache_empty_on_no_refs
```

---

## 🔄 Data Loading Flow

```
┌─────────────────────────────────────────┐
│ Data Sources (JSON)                     │
├─────────────────────────────────────────┤
│ • ONIX_BookProduct_Codelists_Issue_71   │
│ • thema_v1.6_uk.json                    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ scripts/load_reference_codes.py          │
├──────────────────────────────────────────┤
│ 1. Читає JSON файли                      │
│ 2. Для ONIX: flatten + batch            │
│ 3. Для THEMA: BFS тополог. сортинг      │
│ 4. INSERT...ON CONFLICT DO UPDATE       │
│ 5. Soft delete missing codes             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ PostgreSQL 16.11                         │
├──────────────────────────────────────────┤
│ ref_onix_codelists     (4,748 rows)      │
│ ref_thema_subjects     (9,187 rows)      │
│ catalog_products       (100 rows)        │
│ ... (18 деталізованих таблиць)           │
└──────────────────────────────────────────┘
```

---

## 🚀 Запуск

### Завантажити довідники
```bash
PYTHONPATH=/home/ubuntu/onix_project python scripts/load_reference_codes.py
```

### Запустити тести
```bash
cd /home/ubuntu/onix_project && pytest tests/ -v
```

### Підключитися до БД
```bash
psql postgresql://onix_user:onix_secure_pass_2024@localhost:5432/onix_db
```

---

## 🎯 Наступні кроки

1. **API для пошуку**
   - GET /products/search?thema=Y&language=uk
   - GET /products/{isbn}/details
   - Фільтрація по THEMA категоріям

2. **Web Scraping інтеграція**
   - Завантажити реальні книги з yakaboo.ua, vivat.com.ua
   - Маппування їхніх categoria → THEMA коди

3. **MDM (Master Data Management)**
   - Дедублікація книг
   - Мерж дублікатів з різних джерел
   - Визначення "canonical" ISBN

4. **UI Dashboard**
   - Перегляд каталогу
   - Редагування метаданих
   - Моніторинг синхронізації

---

## 📝 Примітки

- **Composite PK для ONIX**: `(list_number, code)` - гарантує унікальність
- **BFS для THEMA**: Вирішує FK violations у багаторівневих ієрархіях
- **UPSERT замість TRUNCATE**: Zero-downtime updates в production
- **Soft delete**: Зберігає historical data для аудиту
- **Cache TTL**: Запобігає частим запитам до довідників
- **Batch processing**: Обходить PostgreSQL parameter limit

---

**Документ оновлено**: 6 січня 2026
**Версія проєкту**: 1.0 (Reference Data + Catalog Models)
