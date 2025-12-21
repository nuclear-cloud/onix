# Scraping Analysis: Vivat.com.ua

**Date**: 2025-12-21
**Target**: `https://vivat.com.ua/`

## Executive Summary
The target is a **Next.js** application. While it behaves like a Single Page App (SPA), it uses Server-Side Rendering (SSR) for initial loads. This is ideal for us.

**Recommended Strategy**: **Lightweight HTML Parsing**.
We do **not** need a heavy headless browser (Playwright/Selenium). All necessary data is embedded in a structured JSON block (`<script id="__NEXT_DATA__">`) within the initial HTML response.

## 1. Data Sources

### Primary: `__NEXT_DATA__`
Every page source contains a script tag:
```html
<script id="__NEXT_DATA__" type="application/json">{ ... }</script>
```
This JSON object contains:
- **Product Details**: Title, ISBN, Description, Attributes (Author, Binding, Pages).
- **Pricing**: Current price, old price, tax status.
- **Category Lists**: Full array of products on category pages.

### Secondary: APIs
- **Sitemap**: `https://vivat.com.ua/sitemap.xml` (Perfect for discovery and update monitoring).
- **Internal API**: `https://vivat.com.ua/jsonapi/product` (Used internally, but `__NEXT_DATA__` is easier to access).
- **Search**: Powered by `api17.multisearch.io` (External service).

## 2. Scraping Strategy

### Step 1: Discovery (The Monitor)
- **Action**: Poll `https://vivat.com.ua/sitemap.xml`.
- **Logic**: 
    - Parse XML.
    - Filter for URLs containing `/product/`.
    - Compare `lastmod` timestamp with our DB.
    - If new/newer -> Add to **Scrape Queue**.

### Step 2: Extraction (The Scraper)
- **Tool**: `httpx` (Python).
- **Action**: GET request to the product URL.
- **Parsing**:
    1. Parse HTML with `BeautifulSoup`.
    2. Extract content of `<script id="__NEXT_DATA__">`.
    3. `json.loads()` the content.
    4. Navigate JSON path: `props.pageProps.product`.

### Step 3: Transformation (The Bridge)
- **Map** Vivat JSON fields to `ProductCreate`:
    - `product.name` -> `ProductCreate.title`
    - `product.code` (or distinct attribute) -> `ProductCreate.isbn_13`
    - `product.attributes` -> Filter for "Автор" -> `ProductCreate.authors`
    - `product.price` -> `ProductCreate.onix_json.prices`

## 3. Technical Constraints
- **Rate Limiting**: Standard politeness applies (1 req/sec).
- **Auth/Headers**: Standard User-Agent required. No complex login needed for public data.
