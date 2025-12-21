# ONIX Book Metadata System

## Introduction
This project is an **AI-First, high-performance backend** for managing book metadata using the **ONIX for Books 3.1** standard. It bridges the gap between structured legacy XML and modern semantic search capabilities.

For a deep dive into the vision, see the [Program Concept](CONCEPT.md).

## Features
- **ONIX 3.1 Compliance**: Automatic validation and high-speed XML generation.
- **AI-Powered Discovery**: Hybrid search combining SQL filters with vector similarity scoring.
- **Web Scraping & Monitoring**: Autonomous change detection and data extraction from Ukrainian bookstores (Vivat).
- **Modern Stack**: Built with FastAPI, SQLAlchemy (Async), PostgreSQL/pgvector, and Next.js data extraction.

## Setup Instructions

### Prerequisites
- Python 3.10+
- PostgreSQL with `pgvector` extension installed.

### Installation
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
   ```

### Running the Application
#### 1. API Server
```bash
python main.py
```
#### 2. Background Scraper Worker
The worker continuously monitors sitemaps and ingests new books into the database.
```bash
python app/worker.py
```

### Management Scripts
- `scripts/test_scrape.py`: Test scraping of a single URL with full JSON dump.
- `scripts/save_scrape.py`: Scrape and save a product to the database (including authors and embeddings).

### Running Tests
```bash
pytest
```

## Project Structure
See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed breakdown of the system components.

```
/
├── app/
│   ├── api/            # Route handlers
│   ├── core/           # Config and DB setup
│   ├── models/         # SQLAlchemy models
│   ├── scraper/        # [NEW] Web scraping & monitoring
│   ├── schemas/        # Pydantic payloads
│   └── services/       # Business logic (ONIX, Validation, Embeddings)
├── data/               # Data storage / exports
├── scripts/            # Management scripts
└── tests/              # Test suite
```
