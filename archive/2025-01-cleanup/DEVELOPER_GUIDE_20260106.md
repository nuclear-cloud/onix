# Developer Guide

## Швидкий старт

### 1. Setup середовища

```bash
cd /home/ubuntu/onix_project

# Активувати venv
source .venv/bin/activate

# Переконатися в наявності .env
cat .env  # DATABASE_URL, OLLAMA_BASE_URL

# Перевірити PostgreSQL
psql postgresql://onix_user:onix_secure_pass_2024@localhost:5432/onix_db -c "SELECT version();"
```

### 2. Завантажити довідники

```bash
PYTHONPATH=/home/ubuntu/onix_project python scripts/load_reference_codes.py

# Очікуваний вивід:
# ✅ Upserted 4748 ONIX codes
# ✅ Upserted 9187 THEMA codes
```

### 3. Запустити тести

```bash
pytest tests/ -v

# Очікувано: 9 passed ✅
```

---

## 📁 File Structure

```
app/
├── core/
│   ├── config.py                    # Settings, logging config
│   ├── database.py                  # AsyncSession, create_async_engine
│   └── logging.py
│
├── models/
│   ├── catalog.py                   # 📌 ОСНОВНІ МОДЕЛІ (see below)
│   ├── codes_v71.py                 # ONIX Enums (ProductForm, etc.)
│   ├── market.py                    # Market & pricing
│   └── __init__.py
│
├── services/
│   ├── catalog_loader.py            # CatalogLoader (cache, THEMA)
│   ├── product_merger.py            # MDM: merge duplicates
│   ├── discovery_service.py         # Web scraping discovery
│   └── __init__.py
│
└── schemas/
    ├── onix_full.py                 # Pydantic for ONIX XML
    └── __init__.py

scripts/
├── load_reference_codes.py          # 📥 Завантажувач довідників
│   ├── load_onix_codelists()
│   └── load_thema_codes()           # (з BFS алгоритмом)
└── seed_configs.py                  # Initialize domain configs

tests/
├── conftest.py                      # Pytest fixtures
├── test_reference_loaders.py        # ONIX & THEMA loader tests
├── test_catalog_loader.py           # CatalogLoader tests
├── test_catalog_loader_validation.py
├── test_market_loader.py
└── test_thema_cache.py
```

---

## 🔧 Типові операції

### Додати нову таблицю деталей до Product

1. **Додати модель** в `app/models/catalog.py`:

```python
class CatalogNewDetail(Base):
    """<NewDetail> entity"""
    __tablename__ = "catalog_new_details"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("catalog_products.id", ondelete="CASCADE"), nullable=False)
    
    # Поля...
    
    product = relationship("CatalogProduct", back_populates="new_details")
```

2. **Додати relationship** до `CatalogProduct`:

```python
# У класі CatalogProduct:
new_details = relationship("CatalogNewDetail", back_populates="product", cascade="all, delete-orphan")
```

3. **Міграція**:

```sql
CREATE TABLE catalog_new_details (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES catalog_products(id) ON DELETE CASCADE,
    -- поля...
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_catalog_new_details_product_id ON catalog_new_details(product_id);
```

4. **Тестування**:

```python
@pytest.mark.asyncio
async def test_catalog_new_detail_relationship():
    product = CatalogProduct(...)
    detail = CatalogNewDetail(product_id=product.id, ...)
    # Перевіримо cascade delete
    session.delete(product)
    # detail повинен бути видалено автоматично
```

---

### Додати валідацію для ONIX кодів

1. **Додати ENUM** в `app/models/codes_v71.py`:

```python
class NewCodeType(str, Enum):
    CODE_01 = "01"
    CODE_02 = "02"
    # ...
```

2. **Використати в моделі**:

```python
class CatalogProduct(Base):
    new_code = Column(SQLEnum(NewCodeType), nullable=False)
```

3. **Валідація при завантаженні**:

```python
# У loader:
if subject_code not in ref_codes:
    raise ValueError(f"Invalid code: {subject_code}")
```

---

### Імплементувати BFS для нової ієрархії

```python
from collections import deque, defaultdict

def bfs_topological_sort(records: List[dict], parent_key: str) -> dict:
    """
    Розпортажує записи по рівнях ієрархії.
    
    Args:
        records: List[{code, parent_code, ...}]
        parent_key: 'parent_code' або 'parentId'
    
    Returns:
        {level: [records]}
    """
    # Step 1: Build adjacency list
    code_to_record = {r[code_key]: r for r in records}
    parent_to_children = defaultdict(list)
    roots = set()
    
    for record in records:
        code = record[code_key]
        parent = record.get(parent_key) or None
        if parent:
            parent_to_children[parent].append(code)
        else:
            roots.add(code)
    
    # Step 2: BFS traversal
    queue = deque([(root, 0) for root in roots])
    levels = {}
    
    while queue:
        code, level = queue.popleft()
        levels[code] = level
        for child in parent_to_children.get(code, []):
            queue.append((child, level + 1))
    
    # Step 3: Group by level
    records_by_level = defaultdict(list)
    for code, level in levels.items():
        records_by_level[level].append(code_to_record[code])
    
    return records_by_level
```

---

## 🧪 Тестування

### Запустити конкретний тест

```bash
pytest tests/test_reference_loaders.py::test_load_thema_uses_bfs_topological_sort -v
```

### Написати новий тест

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_feature():
    # Setup
    session = AsyncMock()
    
    # Execute
    result = await my_function(session)
    
    # Assert
    assert result is not None
    session.execute.assert_called()
```

### Запустити з покриттям

```bash
pytest tests/ --cov=app --cov-report=html
```

---

## 🐛 Debugging

### Enable SQL logging

```python
# У app/core/database.py:
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Інспектувати таблиці

```bash
# List tables
\dt

# Show table structure
\d catalog_products

# Show indexes
\di

# Show constraints
\dC
```

### Query execution time

```python
import time
start = time.time()
result = await session.execute(...)
print(f"Query time: {time.time() - start:.3f}s")
```

---

## 📊 Database Queries

### Check reference data integrity

```sql
-- ONIX codes validation
SELECT COUNT(*) as total, COUNT(DISTINCT code) as unique_codes
FROM ref_onix_codelists;

-- THEMA hierarchy validation
SELECT level, COUNT(*) FROM (
    WITH RECURSIVE thema_levels AS (
        SELECT code, parent_code, 0 as level FROM ref_thema_subjects WHERE parent_code IS NULL
        UNION ALL
        SELECT t.code, t.parent_code, tl.level + 1
        FROM ref_thema_subjects t
        JOIN thema_levels tl ON t.parent_code = tl.code
    )
    SELECT DISTINCT code, level FROM thema_levels
) x
GROUP BY level
ORDER BY level;

-- Check for orphaned codes
SELECT code, parent_code
FROM ref_thema_subjects
WHERE parent_code IS NOT NULL
AND parent_code NOT IN (SELECT code FROM ref_thema_subjects)
LIMIT 10;
```

### Product statistics

```sql
SELECT 
  COUNT(*) as total_products,
  COUNT(DISTINCT publisher_id) as publishers,
  COUNT(CASE WHEN is_ukrainian THEN 1 END) as ukrainian,
  COUNT(DISTINCT product_form) as product_forms
FROM catalog_products;
```

---

## 🔗 Integration Patterns

### Load product with all details

```python
from sqlalchemy.orm import selectinload

async def get_product_full(session, isbn):
    product = await session.execute(
        select(CatalogProduct)
        .options(
            selectinload(CatalogProduct.titles),
            selectinload(CatalogProduct.subjects),
            selectinload(CatalogProduct.languages),
            selectinload(CatalogProduct.contributors).selectinload(CatalogProductContributor.contributor),
            selectinload(CatalogProduct.publisher),
        )
        .where(CatalogProduct.isbn_13 == isbn)
    )
    return product.scalar()
```

### Update product with cascade

```python
async def update_product(session, product_id, new_data):
    product = await session.get(CatalogProduct, product_id)
    
    if new_data.get('titles'):
        product.titles = [
            CatalogTitle(title_text=t['text'], type=t['type'])
            for t in new_data['titles']
        ]
    
    await session.commit()
    # Orphaned titles автоматично видалятимуться (cascade)
```

---

## 📋 Checklist для PR

- [ ] Тести проходять: `pytest tests/ -v`
- [ ] Нові моделі in `app/models/catalog.py`
- [ ] Нові schema validators in `app/schemas/`
- [ ] Міграції документовані
- [ ] FK constraints перевірені
- [ ] Type hints використані
- [ ] Docstrings додані
- [ ] Logging додано для debug
- [ ] Edge cases покриті тестами

---

## 🔐 Security Notes

- Усі FK запити перевіряють `is_active=TRUE` (soft delete working)
- ONIX коди валідуються проти довідника перед вставкою
- THEMA коди гарантують батьків-синів FK integrity
- UUIDs використовуються замість sequential IDs
- async/await запобігає SQL injection

---

## 📚 Посилання

- [SQLAlchemy 2.x Docs](https://docs.sqlalchemy.org/20/)
- [ONIX 3.0 Specification](https://www.editeur.org/143/ONIX/)
- [Thema Classification](https://www.thema.info/)
- [PostgreSQL Async (asyncpg)](https://magicstack.github.io/asyncpg/)

---

**Last Updated**: January 6, 2026  
**Maintainer**: AI Assistant
