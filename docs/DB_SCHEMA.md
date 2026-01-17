# Database Schema - Cold Storage Layer

The current schema is optimized for **Raw Data Ingestion** and **Price History Tracking**. It resides primarily in the `cold` schema of the PostgreSQL database.

## 1. `cold.RawIngestion` (Current Snapshot)

This table stores the most recent version of every product captured from a source.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `BigInt` | Primary Key (Autoincrement) |
| `source` | `VarChar(50)` | Source name (e.g., 'yakaboo') |
| `external_id` | `VarChar(100)` | Unique ID from the source system |
| `code` | `VarChar(100)` | ISBN-13 or EAN (Normalized) |
| `item_type` | `VarChar(50)` | Classified type (BOOK_UA, MERCH, etc.) |
| `status` | `VarChar(50)` | Validation status (NEW, NOCODE) |
| `payload` | `Json` | Full raw JSON record from source |
| `fingerprint` | `VarChar(64)` | SHA256 of the payload (for change detection) |
| `price` | `Decimal(12, 2)` | Latest observed price |
| `downloaded_at` | `Timestamptz` | Last time this record was seen in source |

**Constraints:**
- UNIQUE: `(source, external_id)`
- INDEX: `code`, `fingerprint`

---

## 2. `cold.PriceHistory` (Change Log)

This table records a history of price points. A new entry is created **only** when the observed price differs from the previous one.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `BigInt` | Primary Key |
| `external_id` | `VarChar(100)` | Link to source ID |
| `code` | `VarChar(100)` | ISBN/EAN for quick lookup |
| `price` | `Decimal(12, 2)` | Observed price |
| `source` | `VarChar(50)` | Source name |
| `timestamp` | `Timestamptz` | When the change was detected |

**Indices:**
- `(external_id, timestamp)`: For price trend per item.
- `(code, timestamp)`: For cross-source price comparison.

---

## Architecture Principles (2026)
- **Schema Separation**: Using `cold` schema for staging avoids polluting the `public` schema used for the clean catalog.
- **Fingerprinting**: SHA256 ensures we only update metadata in `RawIngestion` if it actually changed, preventing redundant I/O.
- **Price Delta Logic**: Efficiently handles 1M+ records by avoiding row duplication for identical price points.
