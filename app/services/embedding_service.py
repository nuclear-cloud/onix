from __future__ import annotations

import os
from typing import Optional, Sequence

from prisma import Prisma
from prisma.models import CatalogProduct

# Embedding configuration
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_PROVIDER = os.getenv("PGAI_PROVIDER", "openai")  # used by pgai


def _compose_text(product: CatalogProduct) -> str:
    parts: list[str] = []
    if product.title:
        parts.append(product.title)
    if product.subtitle:
        parts.append(product.subtitle)
    if product.description:
        parts.append(product.description)
    if product.shortDescription:
        parts.append(product.shortDescription)
    if product.publisherName:
        parts.append(f"Publisher: {product.publisherName}")
    if product.language:
        parts.append(f"Lang: {product.language}")
    return "\n\n".join(p for p in parts if p)


async def ensure_extensions(db: Prisma) -> None:
    """Try to enable pgvector/pgai if possible (no-op if not permitted)."""
    try:
        await db.execute_raw("CREATE EXTENSION IF NOT EXISTS vector;")
    except Exception:
        pass
    try:
        await db.execute_raw("CREATE EXTENSION IF NOT EXISTS ai;")
    except Exception:
        pass


async def compute_embedding_via_pgai(db: Prisma, text: str) -> Optional[bytes]:
    """Compute embedding using pgai extension; returns None if not available."""
    # pgai function signatures can vary; try a couple of common forms
    try:
        row = await db.query_first(
            "SELECT ai.embed($1, $2, $3)::vector AS v",
            EMBEDDING_PROVIDER,
            EMBEDDING_MODEL,
            text,
        )
        if row and "v" in row:
            # Prisma returns vector as bytes for Unsupported("vector"), or memoryview
            return row["v"]
    except Exception:
        # fallback attempt for older signature
        try:
            row = await db.query_first(
                "SELECT ai.embedding($1, $2)::vector AS v",
                text,
                EMBEDDING_MODEL,
            )
            if row and "v" in row:
                return row["v"]
        except Exception:
            return None
    return None


async def compute_embedding_via_openai(text: str) -> Optional[list[float]]:
    """Compute embedding with OpenAI python client, if available."""
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return None
    try:
        client = OpenAI()
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        vec = resp.data[0].embedding
        return vec  # list[float]
    except Exception:
        return None


async def upsert_catalog_embedding(db: Prisma, product_id: str, vector_value) -> None:
    """Store embedding into CatalogProduct.embedding.
    vector_value: bytes/memoryview (from pg) or list[float] (python)
    """
    if isinstance(vector_value, (bytes, memoryview)):
        await db.catalogproduct.update(
            where={"id": product_id},
            data={"embedding": vector_value},
        )
        return
    if isinstance(vector_value, list):
        # Use raw SQL to cast python array to vector
        await db.execute_raw(
            "UPDATE catalog_products SET embedding = $1::vector WHERE id = $2",
            vector_value,
            product_id,
        )


async def embed_product(db: Prisma, product_id: str) -> bool:
    """Compute and store embedding for a single CatalogProduct."""
    product = await db.catalogproduct.find_unique(where={"id": product_id})
    if not product:
        return False
    text = _compose_text(product)
    if not text:
        return False

    # Prefer pgai if available
    vec_bytes = await compute_embedding_via_pgai(db, text)
    if vec_bytes is not None:
        await upsert_catalog_embedding(db, product_id, vec_bytes)
        return True

    # Fallback to python OpenAI
    vec = await compute_embedding_via_openai(text)
    if vec is not None:
        await upsert_catalog_embedding(db, product_id, vec)
        return True

    return False


async def semantic_search(db: Prisma, query: str, limit: int = 20) -> list[CatalogProduct]:
    """Do kNN search over CatalogProduct.embedding using pgvector (<->)."""
    # Get query embedding (pgai or python)
    vec_bytes = await compute_embedding_via_pgai(db, query)
    if vec_bytes is None:
        vec = await compute_embedding_via_openai(query)
        if vec is None:
            return []
        # Use $1::vector for python vector input
        rows = await db.query_raw(
            """
            SELECT id
            FROM catalog_products
            WHERE embedding IS NOT NULL
            ORDER BY embedding <-> $1::vector
            LIMIT $2
            """,
            vec,
            limit,
        )
    else:
        rows = await db.query_raw(
            """
            SELECT id
            FROM catalog_products
            WHERE embedding IS NOT NULL
            ORDER BY embedding <-> $1
            LIMIT $2
            """,
            vec_bytes,
            limit,
        )

    ids = [r["id"] if isinstance(r, dict) else r[0] for r in rows]
    if not ids:
        return []
    # Fetch products
    prods = await db.catalogproduct.find_many(
        where={"id": {"in": ids}},
        take=limit,
    )
    # Preserve order roughly
    idpos = {pid: i for i, pid in enumerate(ids)}
    prods.sort(key=lambda p: idpos.get(p.id, 1_000_000))
    return prods
