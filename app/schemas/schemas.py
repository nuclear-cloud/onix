from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
import re


# --- Publisher Schemas ---
class PublisherBase(BaseModel):
    name: str = Field(..., max_length=255, description="ONIX <PublisherName>")
    gln: Optional[str] = Field(None, max_length=13, description="Global Location Number")

class PublisherCreate(PublisherBase):
    pass

class PublisherResponse(PublisherBase):
    id: UUID
    class Config:
        from_attributes = True


# --- Author Schemas ---
class AuthorBase(BaseModel):
    full_name: str = Field(..., max_length=255, description="ONIX <PersonName>")
    biography: Optional[str] = Field(None, description="ONIX <BiographicalNote>")

class AuthorCreate(AuthorBase):
    pass

class AuthorResponse(AuthorBase):
    id: UUID
    class Config:
        from_attributes = True


# --- Collection Schemas ---
class CollectionBase(BaseModel):
    title: str = Field(..., max_length=255, description="ONIX <TitleText>")
    issn: Optional[str] = Field(None, max_length=9, description="ISSN for series")

class CollectionCreate(CollectionBase):
    pass

class CollectionResponse(CollectionBase):
    id: UUID
    class Config:
        from_attributes = True


# --- Product Author Schema ---
class ProductAuthorBase(BaseModel):
    author_id: UUID
    role_code: str = Field("A01", description="ONIX List 17 code, e.g., A01=Author")
    sequence_number: int = Field(1, ge=1)


# --- ONIX Block Schemas (stored in JSONB) ---
class TextContent(BaseModel):
    text_type: str = Field(..., description="ONIX List 153, e.g., 03 for Description")
    content_audience: str = Field("00", description="ONIX List 154")
    text: str

class SupportingResource(BaseModel):
    resource_content_type: str = Field(..., description="ONIX List 158, e.g., 01 for Cover")
    resource_mode: str = Field("03", description="ONIX List 159, e.g., 03 for Image")
    resource_link: str

class Price(BaseModel):
    price_type: str = Field("01", description="ONIX List 58, e.g., 01 for RRP")
    price_amount: float
    currency_code: str = Field("UAH", description="ONIX List 96")
    tax_rate_code: Optional[str] = Field("S", description="ONIX List 62")
    tax_rate_percent: Optional[float] = Field(20.0)

class OnixJson(BaseModel):
    text_content: Optional[List[TextContent]] = None
    supporting_resources: Optional[List[SupportingResource]] = None
    prices: Optional[List[Price]] = None
    subjects: Optional[List[dict]] = None  # For UDC/УДК codes
    extra: Optional[dict] = None  # Catch-all for other ONIX data


# --- Product Schemas ---
class ProductBase(BaseModel):
    isbn_13: str = Field(..., min_length=13, max_length=13)
    title: str = Field(..., max_length=500)
    publisher_id: Optional[UUID] = None
    collection_id: Optional[UUID] = None
    product_form: Optional[str] = Field("BC", description="ONIX List 150, e.g., BC=Paperback")
    language: str = Field("ukr", description="ISO 639-2/B code")
    onix_json: Optional[OnixJson] = None
    
    @field_validator("isbn_13")
    @classmethod
    def validate_isbn(cls, v):
        if not re.match(r"^[0-9]{13}$", v):
            raise ValueError("ISBN-13 must be exactly 13 digits")
        return v

class ProductCreate(ProductBase):
    authors: Optional[List[ProductAuthorBase]] = None

class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    authors: Optional[List[ProductAuthorBase]] = None
    
    class Config:
        from_attributes = True


# --- Search Schemas ---
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    publisher_id: Optional[UUID] = None
    language: Optional[str] = None
    limit: int = Field(10, ge=1, le=100)
