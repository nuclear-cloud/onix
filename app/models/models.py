import uuid
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class Publisher(Base):
    __tablename__ = "publishers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    gln = Column(String(13))
    
    products = relationship("Product", back_populates="publisher")


class Author(Base):
    __tablename__ = "authors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    biography = Column(Text)
    
    products = relationship("ProductAuthor", back_populates="author")


class Collection(Base):
    __tablename__ = "collections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    issn = Column(String(9))
    
    products = relationship("Product", back_populates="collection")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isbn_13 = Column(String(13), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    publisher_id = Column(UUID(as_uuid=True), ForeignKey("publishers.id"))
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"))
    product_form = Column(String(10))
    language = Column(String(3), default="ukr")
    onix_json = Column(JSONB)
    embedding = Column(Vector(384))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    publisher = relationship("Publisher", back_populates="products")
    collection = relationship("Collection", back_populates="products")
    authors = relationship("ProductAuthor", back_populates="product")


class ProductAuthor(Base):
    __tablename__ = "product_authors"
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True)
    role_code = Column(String(10), default="A01")
    sequence_number = Column(Integer, default=1)
    
    product = relationship("Product", back_populates="authors")
    author = relationship("Author", back_populates="products")
