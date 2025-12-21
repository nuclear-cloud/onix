# ONIX Book Metadata System: Concept & Vision

## Vision
To build an **AI-first, high-performance metadata engine** that bridges the gap between the complex, legacy world of ONIX 3.1 XML and the modern needs of digital publishers and data-driven retailers.

## The Problem
The book publishing industry relies on the **ONIX for Books 3.1** standard for exchanging metadata. While robust, ONIX is:
- **Cumbersome**: XML-based and extremely verbose.
- **Strictly Keyword-Based**: Traditional systems struggle with semantic meaning (e.g., finding "dystopian novels about space" if the keyword isn't exactly there).
- **Hard to Validate**: Compliance with thousands of "Codelists" is a nightmare for manual entry.

## Core Pillars

### 1. Semantic Interoperability
We provide a developer-friendly JSON API that abstracts away the complexity of XML. The system acts as a translation layer—ingesting clean data and outputting perfectly formatted, industry-standard ONIX 3.1 XML.

### 2. AI-Driven Discovery (Hybrid Search)
Moving beyond the ISBN. Our system uses **Vector Embeddings** (via `pgvector`) to understand the "essence" of a book. 
- **The Strategy**: Combine structured SQL filters (Publisher, Language, Date) with semantic similarity.
- **The Result**: Publishers can offer search experiences that rival industry giants like Amazon, even with smaller catalogs.

### 3. Automated Compliance
A proactive validation engine that checks data against ONIX 3.1 business rules and codelists *before* it hits the database. No more rejected files from retailers.

### 4. Scalable Export Engine
Generate ONIX XML messages for thousands of products in milliseconds. Designed to integrate into CI/CD pipelines for automated data distribution.

### 5. Web Scraping & Monitoring
An autonomous data gathering engine that:
- **Parses** Ukrainian book websites to build the catalog.
- **Monitors** target sites for new products and price changes.
- **Alerts** the system to ingest new metadata automatically.

## Target Audience
- **Independent Publishers**: Who need professional-grade metadata tools without the enterprise price tag.
- **Retailers/Aggregators**: Who need to ingest diverse ONIX feeds and normalize them for modern search engines.
- **Book-Tech Startups**: Building libraries, review sites, or recommendation engines.

## Future Roadmap
- **Generative Descriptions**: Using LLMs (Groq) to auto-generate marketing copy from basic book data.
- **Visual Metadata**: AI analysis of book covers to extract mood and genre tags.
- **Automatic Codelist Mapping**: Intelligent mapping of internal publisher categories to standard ONIX codes.
