# Prisma Quick Reference

## Setup

```bash
# .env file
PRISMA_DATABASE_URL=postgresql://user:pass@localhost:5432/onix_db

# Install
pip install prisma

# Generate client
prisma generate

# Update from database
prisma db pull && prisma generate
```

## Basic Usage

```python
from prisma import Prisma

async def query():
    db = Prisma()
    await db.connect()
    
    # Your queries here
    
    await db.disconnect()
```

## Common Queries

```python
# Count all
total = await db.catalogproduct.count()

# Count with filter
count = await db.catalogproduct.count(
    where={'isbn13': {'not': None}}
)

# Find by unique field
book = await db.catalogproduct.find_unique(
    where={'isbn13': '9789666023998'}
)

# Find first match
book = await db.catalogproduct.find_first(
    where={'sku': '1492464'}
)

# Find many
books = await db.catalogproduct.find_many(
    where={'isUkrainian': True},
    take=10,
    skip=0,
    order={'createdAt': 'desc'}
)

# With relations
books = await db.catalogproduct.find_many(
    include={
        'publisher': True,
        'titles': True
    },
    take=5
)
```

## Filter Operators

```python
# Equals
where={'isbn13': '9789666023998'}

# Not null
where={'isbn13': {'not': None}}

# In list
where={'isbn13': {'in': ['9789666023998', '9786175517987']}}

# Comparisons
where={'createdAt': {'gte': datetime(2026, 1, 1)}}  # >=
where={'createdAt': {'gt': datetime(2026, 1, 1)}}   # >
where={'createdAt': {'lte': datetime(2026, 1, 31)}} # <=
where={'createdAt': {'lt': datetime(2026, 1, 31)}}  # <

# String matching
where={'sku': {'startswith': '14'}}
where={'sku': {'endswith': '99'}}
where={'sku': {'contains': '123'}}

# AND
where={
    'AND': [
        {'isbn13': {'not': None}},
        {'isUkrainian': True}
    ]
}

# OR
where={
    'OR': [
        {'productForm': 'HARDBACK'},
        {'productForm': 'PAPERBACK'}
    ]
}
```

## Pagination & Sorting

```python
# Paginate
books = await db.catalogproduct.find_many(
    take=10,      # LIMIT
    skip=20,      # OFFSET
    order={'createdAt': 'desc'}
)

# Multiple sort fields
books = await db.catalogproduct.find_many(
    order=[
        {'createdAt': 'desc'},
        {'isbn13': 'asc'}
    ]
)
```

## Relations

```python
# Load related data
books = await db.catalogproduct.find_many(
    include={
        'publisher': True,      # Single relation
        'titles': True,         # Multiple relation
        'contributors': True
    }
)

# Access relations
for book in books:
    print(book.publisher.name)
    print([t.titleText for t in book.titles])
```

## Select Specific Fields

```python
# Only fetch needed columns
book = await db.catalogproduct.find_first(
    where={'isbn13': '9789666023998'},
    select={
        'isbn13': True,
        'sku': True,
        'productForm': True
    }
)
```

## Examples

```bash
# Run examples
python examples/prisma_simple.py
python examples/prisma_advanced.py
```

## Comparison to SQLAlchemy

| Task | Prisma | SQLAlchemy |
|------|--------|------------|
| Count | `db.model.count()` | `session.scalar(select(func.count()).select_from(Model))` |
| Find by ID | `db.model.find_unique(where={'id': '...'})` | `session.get(Model, id)` |
| Filter | `db.model.find_many(where={'field': value})` | `session.scalars(select(Model).where(Model.field == value))` |
| Join | `db.model.find_many(include={'relation': True})` | `session.scalars(select(Model).options(selectinload(Model.relation)))` |

## Full Documentation

See [PRISMA_GUIDE.md](./PRISMA_GUIDE.md)
