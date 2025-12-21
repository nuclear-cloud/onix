"""
Concept: Product API Endpoints

This module defines the RESTful API routes for managing Book Products.
It handles creation, retrieval, searching (hybrid vector+SQL), and ONIX export.
It integrates ValidationService and EmbeddingService into the request flow.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from app.core.database import get_db
from app.models.models import Product, Publisher, Author, Collection, ProductAuthor
from app.schemas.schemas import (
    ProductCreate, ProductResponse, 
    PublisherCreate, PublisherResponse,
    AuthorCreate, AuthorResponse,
    SearchQuery
)
from app.services.onix_service import OnixXmlGenerator
from app.services.embedding_service import EmbeddingService
from app.services.validation_service import ValidationService

router = APIRouter()


# --- Publisher Endpoints ---
@router.post("/publishers", response_model=PublisherResponse)
async def create_publisher(publisher: PublisherCreate, db: AsyncSession = Depends(get_db)):
    db_publisher = Publisher(**publisher.model_dump())
    db.add(db_publisher)
    await db.commit()
    await db.refresh(db_publisher)
    return db_publisher


# --- Author Endpoints ---
@router.post("/authors", response_model=AuthorResponse)
async def create_author(author: AuthorCreate, db: AsyncSession = Depends(get_db)):
    db_author = Author(**author.model_dump())
    db.add(db_author)
    await db.commit()
    await db.refresh(db_author)
    return db_author


# --- Product Endpoints ---
@router.post("/products", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    """Ingest a new product with ONIX metadata and validation."""
    from app.services.product_service import ProductService
    service = ProductService(db)
    try:
        return await service.create_product(product)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/products/{isbn}", response_model=ProductResponse)
async def get_product(isbn: str, db: AsyncSession = Depends(get_db)):
    """Get a product by ISBN-13."""
    result = await db.execute(select(Product).where(Product.isbn_13 == isbn))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не знайдено")
    return product


@router.get("/products/{isbn}/onix", response_class=Response)
async def export_product_onix(isbn: str, db: AsyncSession = Depends(get_db)):
    """Export a product as ONIX 3.1 XML."""
    result = await db.execute(select(Product).where(Product.isbn_13 == isbn))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не знайдено")
    
    # Get related data
    authors = []
    if product.authors:
        author_ids = [pa.author_id for pa in product.authors]
        result = await db.execute(select(Author).where(Author.id.in_(author_ids)))
        authors = result.scalars().all()
    
    publisher = None
    if product.publisher_id:
        result = await db.execute(select(Publisher).where(Publisher.id == product.publisher_id))
        publisher = result.scalar_one_or_none()
    
    collection_title = None
    if product.collection_id:
        result = await db.execute(select(Collection).where(Collection.id == product.collection_id))
        collection = result.scalar_one_or_none()
        if collection:
            collection_title = collection.title
    
    generator = OnixXmlGenerator(sender_name="ONIX Book System")
    xml_content = generator.generate_product_xml(product, authors, publisher, collection_title)
    
    return Response(content=xml_content, media_type="application/xml")


@router.post("/search", response_model=List[ProductResponse])
async def hybrid_search(query: SearchQuery, db: AsyncSession = Depends(get_db)):
    """Perform hybrid search with vector similarity and SQL filters."""
    
    # Generate query embedding
    query_embedding = EmbeddingService.generate_embedding(query.query)
    
    # Build SQL query with vector similarity
    sql = """
        SELECT p.*, 
               1 - (p.embedding <=> :embedding::vector) as similarity
        FROM products p
        WHERE 1=1
    """
    params = {"embedding": str(query_embedding)}
    
    if query.publisher_id:
        sql += " AND p.publisher_id = :publisher_id"
        params["publisher_id"] = str(query.publisher_id)
    
    if query.language:
        sql += " AND p.language = :language"
        params["language"] = query.language
    
    sql += f" ORDER BY similarity DESC LIMIT :limit"
    params["limit"] = query.limit
    
    from sqlalchemy import text
    result = await db.execute(text(sql), params)
    products = result.fetchall()
    
    return [ProductResponse.model_validate(dict(row._mapping)) for row in products]
