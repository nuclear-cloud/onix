# System Architecture

## Overview
The **ONIX Book Metadata System** is a high-performance backend designed to manage, search, and export book metadata compliant with the **ONIX 3.1** standard. It leverages modern AI techniques for hybrid search (semantic + structured) and provides a robust API for integration.

## Technology Stack

### Core Framework
- **Language**: Python 3.12+
- **Web Framework**: FastAPI (High performance, async support)
- **Server**: Uvicorn (ASGI standard)

### Database Layer
- **Primary Database**: PostgreSQL
- **ORM**: SQLAlchemy (AsyncIO)
- **Driver**: `asyncpg`
- **Vector Search**: `pgvector` extension for efficient similarity search
- **Migrations**: (Likely Alembic, though not explicitly seen in file list yet)

### Data Processing & AI
- **XML Processing**: `lxml` for high-performance ONIX XML parsing/generation
- **Validation**: Custom validation service + Pydantic models
- **Embeddings**: `sentence-transformers` for generating vector embeddings of book metadata
- **Future AI**: `groq` integration for generative text tasks

## System Components

### 1. API Layer (`app/api`)
- RESTful endpoints for managing resources:
  - `Products` (Books)
  - `Publishers`
  - `Authors`
- **Search Endpoint**: Supports hybrid search combining SQL filters (publisher, language) with vector similarity scoring.
- **Export Endpoint**: Generates valid ONIX 3.1 XML on the fly for products.

### 2. Service Layer (`app/services`)
- **ProductService**: The primary orchestrator for product ingestion. It coordinates author lookup/creation, embedding generation, and database persistence.
- **OnixXmlGenerator**: Handles the complexity of mapping internal models to the verbose ONIX 3.1 XML structure.
- **ValidationService**: Enforces business rules and ONIX codelist compliance before data persistence.
- **EmbeddingService**: Converts product text (Titles, Descriptions, Authors) into vector embeddings for the database.

### 3. Data Model (`app/models`)
- **Product**: Core entity containing ISBN, title, description, language, and the vector embedding.
- **Author/Publisher**: Relational entities linked to products.
- **Collection**: Series or collection data.

### 4. Scraper Layer (`app/scraper`)
- **ScraperService**: Fetches raw data from external sites (e.g., Vivat.com.ua). Optimized for Next.js sites by extracting `__NEXT_DATA__` JSON.
- **Transformer**: Normalizes messy external data into the strict `ProductCreate` schema. Maps platform-specific attributes (Prices, Images, Authors, **Original Titles**, **Contributors**, **Measures**) to ONIX-compliant structures.
- **MonitorService**: Polls sitemaps and tracks content hashes to automatically detect and ingest new or updated products.

## Data Flow
1. **Ingestion (API)**:
   - Product data is received via API (JSON).
   - `ValidationService` checks against ONIX rules.
   - `EmbeddingService` generates a vector representation of the book.
   - Data is stored in PostgreSQL (relational data + vector).

2. **Ingestion (Scraper)**:
   - `MonitorService` detects new URL in sitemap.
   - `ScraperService` extracts `__NEXT_DATA__`.
   - `Transformer` converts to `ProductCreate` schema.
   - Data is validated and preserved (including Images/PDFs).

3. **Search**:
   - User sends a text query (e.g., "dystopian novels about space").
   - Query is converted to an embedding.
   - Database performs a cosine similarity search via `pgvector`.
   - Results are returned ranked by relevance.

4. **Export**:
   - Application requests an ONIX record for a Book (ISBN).
   - System fetches all related entities (Authors, Publisher).
   - `OnixXmlGenerator` constructs the XML tree.
   - Response is returned as `application/xml`.

## Directory Structure
```
/
├── app/
│   ├── api/            # Route handlers
│   ├── core/           # Config and DB setup
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic payloads
│   └── services/       # Business logic (ONIX, Validation, Embeddings)
├── data/               # Data storage / exports
├── scripts/            # Management scripts
└── tests/              # Test suite
```
