# AGENTS.md - ONIX Aggregator Guidelines

This file provides context and guidelines for AI agents working on the ONIX Aggregator project.

## 🚀 Quick Start & Verification
**Core Commands**
- **Install**: `pip install -r requirements.txt && prisma generate`
- **Run App**: `python main.py` (FastAPI on http://localhost:8000)
- **Run All Tests**: `pytest tests/ -v`
- **Run Single Test**: `pytest tests/test_repositories.py::test_product_search -v`
- **Lint/Format**: Use existing project style (autopep8/black patterns observed).

## 🏗 Architecture & Stack
- **Framework**: FastAPI (Async/Await)
- **Database**: PostgreSQL (Prisma ORM - Source of Truth)
- **Schemas**: `public` (Catalog), `codelist` (ONIX codes)
- **Key Pattern**: 3-Tier Architecture (Router → Service → Repository)
  - `Router`: `app/routers/` (HTTP, Validation)
  - `Service`: `app/services/` (Business Logic, DTO mapping)
  - `Repository`: `app/repositories/` (Prisma Queries)
- **Data Flow**: `Router` calls `Service` → `Service` calls `Repository` → `Repository` executes Prisma query.

## 📝 Code Style & Conventions
**1. Imports**
- Group: Stdlib → Third-party → Local app.
- Local imports should use absolute paths: `from app.core.config import settings`.

**2. Naming**
- **Variables/Functions**: `snake_case` (e.g., `get_product_by_isbn`)
- **Classes**: `PascalCase` (e.g., `PrismaCatalogService`)
- **Files**: `snake_case.py`
- **ONIX Fields**: Keep `isbn13`, `product_form_code` matching DB schema.

**3. Types & DTOs**
- Use **Pydantic V2**: `model_config = ConfigDict(...)` (NOT `class Config`).
- Return DTOs from routers, not raw DB models.
- Use Type hints everywhere: `def func(a: int) -> str:`.

**4. Database Access (Prisma)**
- **NEVER** instantiate `Prisma()` directly in handlers.
- **ALWAYS** use dependency injection: `db: Prisma = Depends(get_db)`.
- **N:N Relations**: Use explicit `include` in queries (e.g., `include={"contributors": {"include": {"contributor": True}}}`).

**5. Error Handling**
- Service layer: Raise specific exceptions (e.g., `ValueError`).
- Router layer: Catch exceptions and raise `HTTPException`.

## 🛡 Copilot/Agent Rules (from .github/copilot-instructions.md)
- **Prisma Client**: Always use `app.core.prisma_db.get_db` for sessions.
- **Schema Changes**:
  1. Edit `prisma/schema.prisma`
  2. Run `prisma generate`
  3. Run `prisma db push` (dev only)
- **Testing**:
  - Mock Prisma client for unit tests.
  - Use `@pytest.mark.asyncio` for async tests.

## ⚠️ Important Notes
- **Context Limit**: Be mindful of large files like `schema.prisma`. Read only relevant sections if possible.
- **Secrets**: NEVER commit `.env` or hardcoded credentials.
- **Legacy Code**: Ignore code in `archive/`. Focus on `app/` and `prisma/`.
- **Environment**: If `DB_USER` is missing in env, defaults are `onix_user`/`onix_pass`.

## 📂 Key Files Map
- `main.py`: App entry point.
- `prisma/schema.prisma`: DB Schema Definition.
- `app/routers/catalog.py`: Main API endpoints.
- `app/services/prisma_catalog_service.py`: Core logic.
- `app/repositories/prisma_repositories.py`: DB queries.
- `tests/`: Pytest suite (38+ tests).
