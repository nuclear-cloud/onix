from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.models import Product, Author, Publisher, Collection, ProductAuthor
from app.schemas.schemas import (
    ProductCreate, ProductResponse, SearchQuery,
    PublisherCreate, PublisherResponse,
    AuthorCreate, AuthorResponse
)
from app.services.onix_service import OnixXmlGenerator
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/api", tags=["Products"])


# --- Publisher Endpoints ---
@router.post("/publishers", response_model=PublisherResponse, status_code=201)
async def create_publisher(publisher: PublisherCreate, db: AsyncSession = Depends(get_db)):
    db_publisher = Publisher(**publisher.model_dump())
    db.add(db_publisher)
    await db.commit()
    await db.refresh(db_publisher)
    return db_publisher


# --- Author Endpoints ---
@router.post("/authors", response_model=AuthorResponse, status_code=201)
async def create_author(author: AuthorCreate, db: AsyncSession = Depends(get_db)):
    db_author = Author(**author.model_dump())
    db.add(db_author)
    await db.commit()
    await db.refresh(db_author)
    return db_author


# --- Product Endpoints ---
@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    """Ingest a new product with ONIX metadata."""
    
    # Check if ISBN already exists
    existing = await db.execute(select(Product).where(Product.isbn_13 == product.isbn_13))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Product with this ISBN-13 already exists")
    
    # Extract annotation for embedding
    annotation = None
    if product.onix_json and product.onix_json.text_content:
        annotations = [tc.text for tc in product.onix_json.text_content if tc.text_type == "03"]
        annotation = annotations[0] if annotations else None
    
    # Get author names for embedding
    author_names = []
    if product.authors:
        author_ids = [a.author_id for a in product.authors]
        result = await db.execute(select(Author).where(Author.id.in_(author_ids)))
        authors = result.scalars().all()
        author_names = [a.full_name for a in authors]
    
    # Generate embedding
    embed_text = EmbeddingService.create_product_text(product.title, author_names, annotation)
    embedding = EmbeddingService.generate_embedding(embed_text)
    
    # Create product
    product_data = product.model_dump(exclude={"authors"})
    if product_data.get("onix_json"):
        product_data["onix_json"] = product_data["onix_json"]
    
    db_product = Product(**product_data, embedding=embedding)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    
    # Add author associations
    if product.authors:
        for author_data in product.authors:
            pa = ProductAuthor(
                product_id=db_product.id,
                author_id=author_data.author_id,
                role_code=author_data.role_code,
                sequence_number=author_data.sequence_number
            )
            db.add(pa)
        await db.commit()
    
    return db_product


@router.get("/products/{isbn}", response_model=ProductResponse)
async def get_product(isbn: str, db: AsyncSession = Depends(get_db)):
    """Get a product by ISBN-13."""
    result = await db.execute(select(Product).where(Product.isbn_13 == isbn))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/products/{isbn}/onix", response_class=Response)
async def export_product_onix(isbn: str, db: AsyncSession = Depends(get_db)):
    """Export a product as ONIX 3.1 XML."""
    result = await db.execute(select(Product).where(Product.isbn_13 == isbn))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
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
