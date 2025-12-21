"""
Concept: Pydantic Schemas

This file defines the data transfer objects (DTOs) used for API validation and serialization.
It ensures that incoming JSON data matches expected formats and provides a structured
`ProductCreate` model that serves as the "Universal Book Object" for the system.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)


# --- Author Schemas ---
class AuthorBase(BaseModel):
    full_name: str = Field(..., max_length=255, description="ONIX <PersonName>")
    biography: Optional[str] = Field(None, description="ONIX <BiographicalNote>")

class AuthorCreate(AuthorBase):
    pass

class AuthorResponse(AuthorBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


# --- Collection Schemas ---
class CollectionBase(BaseModel):
    title: str = Field(..., max_length=255, description="ONIX <TitleText>")
    issn: Optional[str] = Field(None, max_length=9, description="ISSN for series")

class CollectionCreate(CollectionBase):
    pass

class CollectionResponse(CollectionBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


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
    resource_content_type: str = Field(..., description="ONIX List 158, e.g., 01 for Cover, 11 for Video")
    resource_mode: str = Field("03", description="ONIX List 159, e.g., 03 for Image, 04 for Audio, 05 for Video")
    resource_link: str

class Price(BaseModel):
    price_type: str = Field("01", description="ONIX List 58, e.g., 01 for RRP")
    price_amount: float
    currency_code: str = Field("UAH", description="ONIX List 96")
    tax_rate_code: Optional[str] = Field("S", description="ONIX List 62")
    tax_rate_percent: Optional[float] = Field(20.0)

class Subject(BaseModel):
    subject_scheme_identifier: str = Field(..., description="ONIX List 27, e.g., 10 for BISAC, 20 for Keywords")
    subject_code: Optional[str] = None
    subject_heading_text: Optional[str] = None

class Extent(BaseModel):
    extent_type: str = Field(..., description="ONIX List 23, e.g., 00 for Main Content Page Count")
    extent_value: float
    extent_unit: str = Field(..., description="ONIX List 24, e.g., 03 for Pages")

class Measure(BaseModel):
    measure_type: str = Field(..., description="ONIX List 48, e.g., 01 for Height, 02 for Width")
    measurement: float
    measure_unit: str = Field(..., description="ONIX List 50, e.g., mm, g")

class Contributor(BaseModel):
    contributor_role: str = Field(..., description="ONIX List 17, e.g., B06 for Translator, A12 for Illustrator")
    person_name: str
    biographical_note: Optional[str] = None

class TitleDetail(BaseModel):
    title_type: str = Field(..., description="ONIX List 15, e.g., 01 for Distinctive Title, 03 for Original Title")
    title_text: str

class CollectionDetail(BaseModel):
    collection_type: str = Field("10", description="ONIX List 148, 10 for Publisher Collection")
    title_text: str

class ProductAvailability(BaseModel):
    product_availability: str = Field(..., description="ONIX List 65, e.g., 20 for In Stock, 21 for Out of Stock")

class SupplyDetail(BaseModel):
    supplier_name: str = Field(..., description="Name of the supplier (e.g., Vivat)")
    product_availability: str = Field(..., description="ONIX List 65")
    prices: Optional[List[Price]] = None

class OnixJson(BaseModel):
    titles: Optional[List[TitleDetail]] = None
    contributors: Optional[List[Contributor]] = None
    collections: Optional[List[CollectionDetail]] = None
    text_content: Optional[List[TextContent]] = None
    supporting_resources: Optional[List[SupportingResource]] = None
    prices: Optional[List[Price]] = None
    subjects: Optional[List[Subject]] = None
    extents: Optional[List[Extent]] = None
    measures: Optional[List[Measure]] = None
    supply_details: Optional[List[SupplyDetail]] = None
    publishing_date: Optional[str] = None # YYYYMMDD
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
    
    model_config = ConfigDict(from_attributes=True)


# --- Search Schemas ---
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    publisher_id: Optional[UUID] = None
    language: Optional[str] = None
    limit: int = Field(10, ge=1, le=100)
