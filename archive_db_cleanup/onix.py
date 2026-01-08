from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from datetime import datetime

class ProductIdentifier(BaseModel):
    type: str = Field(..., description="ProductIDType code (e.g. '15' for ISBN-13)")
    value: str = Field(..., description="ID value")
    type_name: Optional[str] = Field(None, description="Name for proprietary IDs")

class Title(BaseModel):
    type: str = Field(..., description="TitleType code (e.g. '01' for Distinctive Title)")
    text: str
    language: Optional[str] = None

class Contributor(BaseModel):
    sequence_number: Optional[int] = None
    role: str = Field(..., description="ContributorRole code (e.g. 'A01' for Author)")
    name: str = Field(..., description="PersonName or CorporateName")
    
class Subject(BaseModel):
    scheme: str = Field(..., description="SubjectSchemeIdentifier (e.g. '24' for proprietary)")
    code: Optional[str] = None
    text: Optional[str] = None
    model_config = ConfigDict(extra='allow')
    
class Extent(BaseModel):
    type: str = Field(..., description="ExtentType code (e.g. '00' for Main content page count)")
    value: float
    unit: Optional[str] = Field(None, description="ExtentUnit code (e.g. '03' for Pages)")
    model_config = ConfigDict(extra='allow')

class Publisher(BaseModel):
    role: str = Field(..., description="PublishingRole code (e.g. '01' for Publisher)")
    name: str
    model_config = ConfigDict(extra='allow')

class Price(BaseModel):
    type: str = Field(..., description="PriceType code")
    amount: float
    currency: str = Field(..., description="Currency code (e.g. 'UAH')")
    model_config = ConfigDict(extra='allow')
    
class SupplyDetail(BaseModel):
    supplier_name: Optional[str] = None
    availability: str = Field(..., description="ProductAvailability code")
    prices: List[Price] = []
    model_config = ConfigDict(extra='allow')

class Collection(BaseModel):
    type: str = Field(..., description="CollectionType code (e.g. '10')")
    title: str
    contributor: Optional[str] = None

class ProductFormFeature(BaseModel):
    type: str
    value: str
    description: Optional[str] = None

class Language(BaseModel):
    role: str
    code: str

class RelatedProduct(BaseModel):
    type: str
    identifier: Optional[str] = None
    link: Optional[str] = None

class OnixProduct(BaseModel):
    """ONIX 3.0 Product Subset"""
    model_config = ConfigDict(extra='allow')

    record_reference: Optional[str] = None
    notification_type: str = Field("03", description="03 = Notification confirmed")
    
    product_identifier: List[ProductIdentifier] = []
    titles: List[Title] = []
    contributors: List[Contributor] = []
    subjects: List[Subject] = []
    extents: List[Extent] = []
    languages: List[Language] = []
    publishers: List[Publisher] = []
    collections: List[Collection] = []
    
    product_form: Optional[str] = None
    product_form_detail: Optional[str] = None
    product_form_feature: List[ProductFormFeature] = []
    
    edition: Optional[Dict[str, str]] = None
    
    supporting_resources: List[Dict[str, Any]] = []
    prices: List[Price] = []
    supply_detail: List[SupplyDetail] = []
    related_products: List[RelatedProduct] = []
    audience: List[Dict[str, Any]] = []
    
    # Extra container for non-standard data
    extra: Dict[str, Any] = Field(default_factory=dict)
