# APP LAYER KNOWLEDGE BASE

## OVERVIEW
The `app/` directory houses the core business logic and data processing pipelines of the ONIX Aggregator. It is architected as a modular ETL (Extract, Transform, Load) system that prioritizes reliability and source-agnostic processing. By decoupling the engine logic from source-specific data structures through a declarative adapter system, the application can ingest data from any book retailer with minimal code changes.

## STRUCTURE
- **`core/engine/`**: The execution core. It contains the `UniversalWorker` class, which is responsible for pulling tasks from Redis, applying transformations, and managing persistence in a fault-tolerant manner.
- **`core/adapters/`**: A repository of JSON-based mapping configurations. Each file defines the source-to-target field mapping, extraction paths (using dot notation or list filters), and validation rules for a specific external data source.
- **`classifiers/`**: A specialized module for data sanitization. It handles the validation of ISBNs, EANs, and ISSNs, including the conversion of ISBN-10 to ISBN-13 and region-based classification of items (e.g., Ukrainian vs. English books).

## WHERE TO LOOK
- **Reliable Worker Loop**: `UniversalWorker.run()` in `core/engine/worker.py`. This is the primary entry point for task processing, utilizing Redis `BRPOPLPUSH` to ensure that tasks are moved to a hidden "processing" queue before execution.
- **Mapping & Extraction**: `UniversalWorker._extract_value()` in `core/engine/worker.py`. This recursive method implements the logic for traversing nested JSON objects and filtering arrays based on the patterns defined in the adapters.
- **Stateful Change Detection**: `_handle_data_row()` in `core/engine/worker.py`. It performs a SHA-256 hash check on incoming raw data against the stored version to avoid redundant database writes and accurately log price history.
- **Concurrency Control**: `_acquire_lock()` and `_release_lock()` in the worker logic. These methods implement distributed locking via Redis to prevent multiple workers from conflicting on the same record during processing.

## CONVENTIONS
- **Reliable Task Lifecycle**: Tasks must always exist in either a main queue, a processing queue, or a Dead Letter Queue (DLQ). They are never deleted until a successful database commit is acknowledged via `LREM`.
- **Error Recovery & Retries**: 
  - **Transient Errors**: Database connection issues or temporary timeouts trigger `_requeue_with_retry()`, which manages retry attempts via a `_retry_count` metadata field.
  - **Permanent Failures**: Logic errors or invalid data formats are sent to `_move_to_dlq()`, preserving the message for manual inspection and troubleshooting.
- **Strict Normalization**: No record should enter the database with raw, unformatted identifiers. All ISBNs must pass through `classify_item` to be standardized into ISBN-13 format.
- **Asynchronous Operations**: The entire `app/` layer is built on `asyncio`. All I/O operations, including Redis and Database access via Prisma, must use `await` to maintain high throughput and non-blocking execution.
