# Prisma ORM Integration

## Overview

Prisma is a modern database toolkit that provides type-safe database access with auto-completion. This project now supports **both SQLAlchemy and Prisma** for database operations.

## Why Prisma?

- ✅ **Type-safe queries** with auto-completion in IDEs
- ✅ **Modern syntax** - cleaner, more readable than raw SQL
- ✅ **Auto-generated client** from database schema
- ✅ **Excellent documentation** and community support
- ✅ **Async/await support** built-in

## Setup

### Installation

```bash
pip install prisma
```

### Database Configuration

Add to your `.env` file:

```bash
# For SQLAlchemy (existing)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/onix_db

# For Prisma (new - note: no +asyncpg driver)
PRISMA_DATABASE_URL=postgresql://user:pass@localhost:5432/onix_db
```

### Generate Client

After database schema changes:

```bash
# Introspect database and update schema
prisma db pull

# Generate Python client
prisma generate
```

## Usage Examples

### Basic Queries

```python
from prisma import Prisma

async def example():
    db = Prisma()
    await db.connect()
    
    # Count all books
    total = await db.catalogproduct.count()
    print(f"Total books: {total:,}")
    
    # Find by ISBN
    book = await db.catalogproduct.find_unique(
        where={'isbn13': '9789666023998'}
    )
    
    # Find many with filters
    hardbacks = await db.catalogproduct.find_many(
        where={'productForm': 'HARDBACK'},
        take=10
    )
    
    await db.disconnect()
```

### Filtering and Pagination

```python
# Pagination
books = await db.catalogproduct.find_many(
    where={'isbn13': {'not': None}},
    skip=0,    # Offset
    take=10,   # Limit
    order={'createdAt': 'desc'}
)

# Complex filters with AND
recent = await db.catalogproduct.find_many(
    where={
        'AND': [
            {'isbn13': {'not': None}},
            {'isUkrainian': True},
            {'createdAt': {'gte': datetime(2026, 1, 6)}}
        ]
    }
)

# Pattern matching
search = await db.catalogproduct.find_many(
    where={'sku': {'startswith': '14'}}
)
```

### Relations (Joins)

```python
# Include related publisher
books = await db.catalogproduct.find_many(
    where={'publisherId': {'not': None}},
    include={
        'publisher': True,    # LEFT JOIN publishers
        'titles': True,       # LEFT JOIN catalog_titles
        'contributors': True  # LEFT JOIN catalog_product_contributors
    },
    take=10
)

for book in books:
    print(f"Book: {book.isbn13}")
    print(f"Publisher: {book.publisher.name}")
    print(f"Titles: {[t.titleText for t in book.titles]}")
```

### Aggregations

```python
# Count with grouping
with_publisher = await db.catalogproduct.count(
    where={'publisherId': {'not': None}}
)

without_publisher = await db.catalogproduct.count(
    where={'publisherId': None}
)

print(f"With publisher: {with_publisher:,}")
print(f"Without publisher: {without_publisher:,}")
```

### Batch Operations

```python
# Find multiple by ISBNs
isbns = ['9789666023998', '9786175517987', '9786175222294']

books = await db.catalogproduct.find_many(
    where={'isbn13': {'in': isbns}}
)

print(f"Found {len(books)} books")
```

## Prisma vs SQLAlchemy

### When to Use Prisma

✅ **New features**: Modern, type-safe queries  
✅ **Read-heavy operations**: Cleaner query syntax  
✅ **Complex joins**: More intuitive relation loading  
✅ **Prototyping**: Faster development with auto-completion

### When to Use SQLAlchemy

✅ **Existing code**: No need to rewrite  
✅ **Raw SQL**: When you need full SQL control  
✅ **Complex migrations**: Better migration tools  
✅ **Legacy patterns**: If team prefers ORM pattern

### Using Both Together

You can use both in the same project:

```python
from prisma import Prisma
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_async_session

async def hybrid_example():
    # Use Prisma for clean reads
    prisma_db = Prisma()
    await prisma_db.connect()
    
    books = await prisma_db.catalogproduct.find_many(
        where={'isbn13': {'not': None}},
        take=100
    )
    
    # Use SQLAlchemy for complex writes
    async with get_async_session() as session:
        # Your existing SQLAlchemy code
        pass
    
    await prisma_db.disconnect()
```

## Available Models

Prisma schema includes all database tables:

- `CatalogProduct` - Main book catalog
- `Publisher` - Publisher information
- `Contributor` - Authors, editors, translators
- `CatalogTitle` - Book titles
- `CatalogProductContributor` - Book-contributor relations
- `CatalogMeasure` - Book dimensions
- `CatalogExtent` - Page counts, durations
- `CatalogSubject` - THEMA, BISAC codes
- `CatalogLanguage` - Language codes
- `CatalogTextContent` - Descriptions, reviews
- And 20+ more tables...

## Query Builder Features

### Filters

```python
# Equality
where={'isbn13': '9789666023998'}

# Not equal
where={'isbn13': {'not': None}}

# In list
where={'isbn13': {'in': ['9789666023998', '9786175517987']}}

# Comparisons
where={'createdAt': {'gte': datetime(2026, 1, 1)}}
where={'createdAt': {'lt': datetime(2026, 1, 31)}}

# Pattern matching
where={'sku': {'startswith': '14'}}
where={'sku': {'endswith': '99'}}
where={'sku': {'contains': '123'}}

# Boolean logic
where={'AND': [{'isbn13': {'not': None}}, {'isUkrainian': True}]}
where={'OR': [{'productForm': 'HARDBACK'}, {'productForm': 'PAPERBACK'}]}
```

### Ordering

```python
# Single field
order={'createdAt': 'desc'}

# Multiple fields
order=[{'createdAt': 'desc'}, {'isbn13': 'asc'}]
```

### Selecting Fields

```python
# Select specific fields only
book = await db.catalogproduct.find_first(
    select={
        'isbn13': True,
        'sku': True,
        'productForm': True
    }
)
```

## Examples

See working examples:

- [examples/prisma_simple.py](../examples/prisma_simple.py) - Basic queries
- [examples/prisma_advanced.py](../examples/prisma_advanced.py) - Complex queries with relations
- [examples/prisma_examples.py](../examples/prisma_examples.py) - Comprehensive examples (old version)

Run them:

```bash
python examples/prisma_simple.py
python examples/prisma_advanced.py
```

## Schema Management

### Update Schema from Database

When database changes (new columns, tables, etc):

```bash
# Pull changes from database
prisma db pull

# Regenerate client
prisma generate
```

### Manual Schema Edits

Edit `prisma/schema.prisma` if needed, then:

```bash
prisma generate
```

## Performance Tips

1. **Use select** to fetch only needed fields
2. **Use pagination** (take/skip) for large result sets
3. **Index columns** used in WHERE clauses
4. **Use include sparingly** - only load relations you need
5. **Batch queries** with `find_many` and `in` filters

## Troubleshooting

### Client Not Found

```bash
prisma generate
```

### Schema Mismatch

```bash
prisma db pull  # Regenerate from database
prisma generate
```

### Decimal Type Error

Already configured in `schema.prisma`:

```prisma
generator client {
  provider                    = "prisma-client-py"
  enable_experimental_decimal = true
}
```

## References

- [Prisma Python Docs](https://prisma-client-py.readthedocs.io/)
- [Prisma Query Reference](https://www.prisma.io/docs/reference/api-reference/prisma-client-reference)
- [Schema.prisma](../prisma/schema.prisma) - Current schema

## Next Steps

1. Try the examples: `python examples/prisma_simple.py`
2. Read the [Prisma Python documentation](https://prisma-client-py.readthedocs.io/)
3. Experiment with your own queries
4. Consider migrating read-heavy operations to Prisma for cleaner code
