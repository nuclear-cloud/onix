# 📚 ONIX Project Documentation Index

## 🎯 Для новачків

**Почніть звідси:**

1. [README.md](README.md) - Загальний опис проєкту
2. [PROJECT_STATUS.md](PROJECT_STATUS.md) - **⭐ ПОТОЧНИЙ СТАТУС** (все що зараз реалізовано)
3. [ARCHITECTURE.md](ARCHITECTURE.md) - Архітектура БД та ER діаграми
4. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Як почати кодити

---

## 📖 Детальна документація

### Дизайн & Архітектура
- **[ARCHITECTURE.md](ARCHITECTURE.md)**
  - Database diagram (DBML)
  - Entity-Relationship diagram
  - Data flow diagram
  - Query patterns
  - Performance metrics

### Розробка & Кодинг
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)**
  - Швидкий старт
  - Типові операції (додавання таблиць, валідація)
  - BFS алгоритм для ієрархій
  - Тестування (unit, integration)
  - Database queries
  - Security notes

### Огляд стану проєкту
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)**
  - ✅ Що реалізовано
  - 📊 Статистика БД
  - 🧪 Результати тестів
  - 🔄 Data loading flow
  - 🚀 Наступні кроки

### Планування & Roadmap
- **[IMPROVEMENTS_ROADMAP.md](IMPROVEMENTS_ROADMAP.md)**
  - Priority 1: API endpoints
  - Priority 2: Web scraping
  - Priority 3: MDM merge
  - Estimated effort & timeline

---

## 🔍 By Topic

### Reference Data (Довідники)

**ONIX Коди** (4,748)
```
Файл: ONIX_BookProduct_Codelists_Issue_71.json
Таблиця: ref_onix_codelists
Структура: Composite PK (list_number, code)
Завантаження: scripts/load_reference_codes.py
```

**THEMA Класифікація** (9,187)
```
Файл: thema_v1.6_uk.json
Таблиця: ref_thema_subjects
Структура: Self-referential FK для ієрархій
Алгоритм: BFS топологічний сортинг
Завантаження: scripts/load_reference_codes.py
```

→ Див: [PROJECT_STATUS.md#1️⃣-довідники](PROJECT_STATUS.md#1️⃣-довідники)

### Book Catalog (Каталог книг)

**19 таблиць** структурованих як:
- `catalog_products` (основна) ← 100 записів
- Detail tables (titles, subjects, languages, etc.)
- Reference links (FK → ref_onix, ref_thema)

→ Див: [ARCHITECTURE.md#entity-relationship-diagram](ARCHITECTURE.md#entity-relationship-diagram)

### Database Operations

**Завантаження даних**
- ONIX: Flat structure → batch INSERT
- THEMA: BFS + level-by-level insertion

**UPSERT семантика**
- ON CONFLICT DO UPDATE (zero-downtime)
- Soft delete (is_active = FALSE)

→ Див: [DEVELOPER_GUIDE.md#database-queries](DEVELOPER_GUIDE.md#database-queries)

---

## 🧪 Testing

**Status**: 9/9 passed ✅

```
tests/test_reference_loaders.py
  ✅ ONIX loader structure
  ✅ THEMA BFS topological sort

tests/test_catalog_loader.py
  ✅ Cache instantiation

tests/test_catalog_loader_validation.py
  ✅ THEMA validation

tests/test_market_loader.py
  ✅ Price updates

tests/test_thema_cache.py
  ✅ Cache TTL behavior
```

**Запуск тестів**:
```bash
cd /home/ubuntu/onix_project
pytest tests/ -v
```

→ Див: [DEVELOPER_GUIDE.md#🧪-тестування](DEVELOPER_GUIDE.md#🧪-тестування)

---

## 🚀 Quick Commands

### Database
```bash
# Підключитися
psql postgresql://onix_user:onix_secure_pass_2024@localhost:5432/onix_db

# Показати таблиці
\dt

# Таблиці каталогу
\dt catalog_*
```

### Завантаження
```bash
# Завантажити усі довідники
PYTHONPATH=/home/ubuntu/onix_project python scripts/load_reference_codes.py
```

### Тестування
```bash
# Усі тести
pytest tests/ -v

# Конкретний тест
pytest tests/test_reference_loaders.py -v

# З покриттям
pytest tests/ --cov=app --cov-report=html
```

---

## 📊 Current Stats

| Компонент | Статус |
|-----------|--------|
| **Reference Data** | ✅ 13,935 кодів завантажено |
| **Book Tables** | ✅ 19 таблиць, 100 записів |
| **Tests** | ✅ 9/9 passing |
| **BFS Algorithm** | ✅ Multi-level hierarchy working |
| **UPSERT Logic** | ✅ Zero-downtime updates |
| **Soft Delete** | ✅ Historical audit trail |
| **Cache TTL** | ✅ 1-hour cache implemented |

---

## 🎯 Roadmap Status

### ✅ Phase 1: Reference Data (COMPLETED)
- ONIX codelists loaded
- THEMA hierarchy loaded
- FK constraints validated

### ⏳ Phase 2: API & Web Scraping (PLANNED)
- REST API for product search
- THEMA-based filtering
- Web scraper for yakaboo, vivat

### ⏳ Phase 3: MDM & Merge (PLANNED)
- Duplicate detection
- Data quality scoring
- Master record creation

---

## 📚 File Manifest

```
/home/ubuntu/onix_project/
├── 📖 Documentation
│   ├── README.md                    # Main project README
│   ├── README_UA.md                 # Ukrainian README
│   ├── PROJECT_STATUS.md            # ⭐ CURRENT STATUS
│   ├── ARCHITECTURE.md              # DB design & diagrams
│   ├── DEVELOPER_GUIDE.md           # How to code
│   ├── DOCUMENTATION_INDEX.md       # This file
│   ├── IMPROVEMENTS_ROADMAP.md      # Future work
│   └── SENIOR_CODE_REVIEW.md        # Code quality notes
│
├── 🐍 Python Code
│   ├── app/models/catalog.py        # 📌 Main models (400+ lines)
│   ├── app/services/
│   ├── scripts/load_reference_codes.py  # 📥 BFS loader
│   └── tests/                       # 🧪 9 unit tests
│
├── 💾 Data
│   ├── data/ONIX_BookProduct_Codelists_Issue_71.json
│   ├── data/thema_v1.6_uk.json
│   └── data/... (analysis reports)
│
└── 📋 Configuration
    ├── docker-compose.yml
    ├── requirements.txt
    ├── pytest.ini
    └── .env (DATABASE_URL, etc.)
```

---

## 🔗 Key Files to Know

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `app/models/catalog.py` | 📌 Core models | 405 | ✅ Complete |
| `scripts/load_reference_codes.py` | 📥 Data loader | 350+ | ✅ BFS working |
| `tests/test_reference_loaders.py` | 🧪 Tests | 100 | ✅ 2/2 passing |
| `ARCHITECTURE.md` | 📐 Design | 300+ | ✅ Complete |
| `DEVELOPER_GUIDE.md` | 👨‍💻 How-to | 400+ | ✅ Complete |

---

## ❓ FAQ

**Q: Де дані про довідники?**  
A: `data/ONIX_BookProduct_Codelists_Issue_71.json` та `data/thema_v1.6_uk.json`

**Q: Як запустити проєкт?**  
A: Див [DEVELOPER_GUIDE.md#швидкий-старт](DEVELOPER_GUIDE.md#швидкий-старт)

**Q: Як додати нову таблицю?**  
A: Див [DEVELOPER_GUIDE.md#додати-нову-таблицю](DEVELOPER_GUIDE.md#додати-нову-таблицю)

**Q: Як написати тест?**  
A: Див [DEVELOPER_GUIDE.md#написати-новий-тест](DEVELOPER_GUIDE.md#написати-новий-тест)

**Q: Що таке BFS алгоритм?**  
A: Див [DEVELOPER_GUIDE.md#імплементувати-bfs](DEVELOPER_GUIDE.md#імплементувати-bfs-для-нової-ієрархії)

---

## 👥 Project History

**January 6, 2026**
- ✅ Composite PK для ONIX
- ✅ BFS топологічна сортування
- ✅ UPSERT zero-downtime updates
- ✅ Soft delete архітектура
- ✅ 1-hour cache TTL
- ✅ 9/9 тестів passing
- ✅ **Документація завершена**

---

**Версія документації**: 1.0  
**Останнє оновлення**: January 6, 2026  
**Відповідальний**: AI Assistant  
**Статус**: ✅ Актуально
