"""
Concept: Product Service

This service handles the core business logic for managing products.
It encapsulates database operations, validation calls, and embedding generation,
allowing product creation to be shared between the API and background workers.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException

from app.models.models import Product, Publisher, Author, Collection, ProductAuthor
from app.schemas.schemas import ProductCreate, ProductAuthorBase, AuthorCreate
from app.services.validation_service import ValidationService
from app.services.embedding_service import EmbeddingService

class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.validator = ValidationService(db)

    async def create_product(self, product: ProductCreate) -> Product:
        """
        Create a new product with full validation and embedding generation.
        """
        # 1. Real-time ONIX Codelist Validation
        errors = await self.validator.validate_product_metadata(product.model_dump())
        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")

        # Check if ISBN already exists
        result = await self.db.execute(select(Product).where(Product.isbn_13 == product.isbn_13))
        existing_product = result.scalar_one_or_none()
        
        # If exists, we might want to update it? For now, we'll error or skip.
        # But for the worker, we might want `upsert`. 
        # Let's keep it simple: Error if exists, treating it as "New Product" flow.
        if existing_product:
            raise ValueError(f"Product with ISBN {product.isbn_13} already exists")
        
        # Get author names for embedding
        author_names = []
        annotation = ""
        if product.onix_json and product.onix_json.text_content:
            for text_item in product.onix_json.text_content:
                if text_item.text_type == "03":  # Description
                    annotation = text_item.text
        
        if product.authors:
            # Note: This assumes authors already exist in DB. 
            # If coming from scraper, we might need to create them dynamically?
            # The current API logic expects IDs. The scraper creates "Text" authors but no IDs.
            # We need logic here to Handle "By Name" authors if IDs are missing.
            # But ProductCreate schema requires `author_id`.
            # This is a gap. The Scraper produces "Authors" list of STRINGS.
            # ProductCreate expects `ProductAuthorBase` with UUIDs.
            # I need to handle this lookup/creation.
            pass

        # For the Scraper integration, we need a way to `get_or_create_author`.
        # I will address this in the worker or helper method.
        # For now, let's stick to the exact logic from the API.

        if product.authors:
            author_ids = [pa.author_id for pa in product.authors]
            result = await self.db.execute(select(Author).where(Author.id.in_(author_ids)))
            authors = result.scalars().all()
            author_names = [a.full_name for a in authors]
        
        # Generate embedding
        embed_text = EmbeddingService.create_product_text(product.title, author_names, annotation)
        embedding = EmbeddingService.generate_embedding(embed_text)
        
        # Create product
        product_data = product.model_dump(exclude={"authors"})
        db_product = Product(**product_data, embedding=embedding)
        self.db.add(db_product)
        # We don't commit here to allow transaction control by caller? 
        # API usually commits. Let's commit here for simplicity of service method.
        await self.db.commit()
        await self.db.refresh(db_product)
        
        # Add author associations
        if product.authors:
            for author_data in product.authors:
                pa = ProductAuthor(
                    product_id=db_product.id,
                    author_id=author_data.author_id,
                    role_code=author_data.role_code,
                    sequence_number=author_data.sequence_number
                )
                self.db.add(pa)
            await self.db.commit()
        
        return db_product

    async def get_or_create_author(self, name: str) -> Author:
        """Find an author by name or create a new one."""
        result = await self.db.execute(select(Author).where(Author.full_name == name))
        author = result.scalar_one_or_none()
        
        if not author:
            author = Author(full_name=name)
            self.db.add(author)
            await self.db.commit()
            await self.db.refresh(author)
            
        return author

    async def ingest_product(self, product_data: ProductCreate, author_names: list[str]) -> Product:
        """
        Ingest a scraped product, handling author creation/lookup automatically.
        """
        # Resolve authors
        product_authors = []
        for i, name in enumerate(author_names):
            author = await self.get_or_create_author(name)
            product_authors.append(ProductAuthorBase(
                author_id=author.id,
                role_code="A01", # Default to Author
                sequence_number=i+1
            ))
        
        # Attach resolved authors to the product DTO
        product_data.authors = product_authors
        
        # Create the product
        # Should catch "already exists" and maybe update? 
        # For now, just try to create.
        try:
            return await self.create_product(product_data)
        except ValueError as e:
            if "already exists" in str(e):
                # Optionally fetch and return existing? or just re-raise
                print(f"Skipping existing product: {product_data.isbn_13}")
                return None
            raise e
