# ONIX Aggregator

**Централізований каталог книг та агрегатор цін для України**

Система для агрегації метаданих книг та цін від рітейлерів, на основі стандарту **ONIX for Books 3.0**.

## 🏗 Архітектура

- **ORM**: Prisma (Python client v0.15.0)
- **База даних**: PostgreSQL з двома схемами:
  - `public` - основні дані (товари, автори, теми)
  - `codelist` - довідники ONIX кодів

## 📊 Статистика

| Таблиця | Записів |
|---------|---------|
| Товари | 69,375 |
| Унікальні автори | 26,879 |
| Унікальні теми | 54,129 |
| Зв'язки товар-автор | 88,084 |
| Зв'язки товар-тема | 604,207 |

## 🛠 Технології

- Python 3.12+
- PostgreSQL 14+
- Prisma ORM 0.15.0
- FastAPI
- Pydantic v2

## 🚀 Швидкий старт

```bash
# 1. Налаштування
cd onix_project && source .venv/bin/activate

# 2. Середовище
cat > .env << 'EOF'
DATABASE_URL=postgresql://user:pass@localhost:5432/onix_db
PRISMA_DATABASE_URL=postgresql://user:pass@localhost:5432/onix_db
EOF

# 3. Генерація Prisma клієнта
prisma generate

# 4. Запуск API
python main.py  # http://localhost:8000/docs
```

## 🧪 Тестування

```bash
pytest tests/ -v
```

## 📂 Структура

```
onix_project/
├── main.py                     # FastAPI entry point
├── prisma/schema.prisma        # Database schema
├── app/
│   ├── core/prisma_db.py       # Prisma client
│   ├── models/                 # Enums, ONIX codes
│   ├── repositories/           # Data access (Prisma)
│   ├── services/               # Business logic
│   ├── routers/                # API endpoints
│   └── schemas/                # Pydantic DTOs
├── scripts/                    # Import scripts
└── tests/                      # Pytest tests
```

## 📡 API Endpoints

| Endpoint | Опис |
|----------|------|
| `GET /catalog/products` | Список товарів |
| `GET /catalog/products/{isbn13}` | Деталі за ISBN |
| `GET /catalog/search?q=` | Пошук |
| `GET /catalog/stats` | Статистика |

## 📚 Документація

- **API Docs**: http://localhost:8000/docs
- **Prisma Studio**: `npx prisma studio`
- **Mapping**: `docs/YAKABOO_SIMPLE_MAPPING.md`
