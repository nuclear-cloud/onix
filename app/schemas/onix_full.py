"""
ONIX 3.0 Full Product Schema.
Strict Pydantic models based on ONIX for Books 3.0.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from app.models.codes_v71 import (
    ProductIdentifierType,
    NotificationType,
    ProductForm,
    ProductFormDetail,
    TitleType,
    ContributorRole,
    LanguageRole,
    SubjectSchemeIdentifier,
    ExtentType,
    MeasureType,
    MeasureUnit,
    TextContentType,
    PublishingDateRole,
    PriceType,
    CollectionType,
    CollectionSequenceType,
    ProductRelation
)

class OnixBaseModel(BaseModel):
    class Config:
        populate_by_name = True
        use_enum_values = True

# --- Sub-components ---

class ProductIdentifier(OnixBaseModel):
    product_id_type: ProductIdentifierType = Field(..., alias="ProductIDType")
    id_value: str = Field(..., alias="IDValue")

class TitleElement(OnixBaseModel):
    title_element_level: str = Field("01", alias="TitleElementLevel")
    title_text: str = Field(..., alias="TitleText")
    subtitle: Optional[str] = Field(None, alias="Subtitle")

class TitleDetail(OnixBaseModel):
    title_type: TitleType = Field(..., alias="TitleType")
    title_element: List[TitleElement] = Field(..., alias="TitleElement")

class Contributor(OnixBaseModel):
    sequence_number: Optional[int] = Field(None, alias="SequenceNumber")
    contributor_role: List[ContributorRole] = Field(..., alias="ContributorRole")
    person_name: Optional[str] = Field(None, alias="PersonName")
    person_name_inverted: Optional[str] = Field(None, alias="PersonNameInverted")
    biographical_note: Optional[str] = Field(None, alias="BiographicalNote")

class Language(OnixBaseModel):
    language_role: LanguageRole = Field(..., alias="LanguageRole")
    language_code: str = Field(..., alias="LanguageCode") # ISO 639-2b

class Subject(OnixBaseModel):
    subject_scheme_identifier: SubjectSchemeIdentifier = Field(..., alias="SubjectSchemeIdentifier")
    subject_code: Optional[str] = Field(None, alias="SubjectCode")
    subject_heading_text: Optional[str] = Field(None, alias="SubjectHeadingText")

class Extent(OnixBaseModel):
    extent_type: ExtentType = Field(..., alias="ExtentType")
    extent_value: float = Field(..., alias="ExtentValue")
    extent_unit: str = Field(..., alias="ExtentUnit")

class Measure(OnixBaseModel):
    measure_type: MeasureType = Field(..., alias="MeasureType")
    measurement: float = Field(..., alias="Measurement")
    measure_unit_code: MeasureUnit = Field(..., alias="MeasureUnitCode")

class AudienceRange(OnixBaseModel):
    audience_range_qualifier: str = Field(..., alias="AudienceRangeQualifier")
    audience_range_precision: str = Field(..., alias="AudienceRangePrecision")
    audience_range_value: str = Field(..., alias="AudienceRangeValue")

class TextContent(OnixBaseModel):
    text_type: TextContentType = Field(..., alias="TextType")
    content_audience: str = Field("00", alias="ContentAudience")
    text: str = Field(..., alias="Text")

class SupportingResource(OnixBaseModel):
    resource_content_type: str = Field(..., alias="ResourceContentType")
    resource_mode: str = Field(..., alias="ResourceMode")
    resource_version: List[Dict[str, Any]] = Field(..., alias="ResourceVersion")

class CollectionIdentifier(OnixBaseModel):
    collection_id_type: str = Field(..., alias="CollectionIDType")
    id_value: str = Field(..., alias="IDValue")

class CollectionSequence(OnixBaseModel):
    collection_sequence_type: CollectionSequenceType = Field(..., alias="CollectionSequenceType")
    collection_sequence_number: str = Field(..., alias="CollectionSequenceNumber")

class Collection(OnixBaseModel):
    collection_type: CollectionType = Field(..., alias="CollectionType")
    collection_identifier: Optional[List[CollectionIdentifier]] = Field(None, alias="CollectionIdentifier")
    title_detail: List[TitleDetail] = Field(..., alias="TitleDetail")
    collection_sequence: Optional[List[CollectionSequence]] = Field(None, alias="CollectionSequence")

class PublishingDate(OnixBaseModel):
    publishing_date_role: PublishingDateRole = Field(..., alias="PublishingDateRole")
    date_format: str = Field("00", alias="DateFormat")
    date_value: str = Field(..., alias="Date")

class Publisher(OnixBaseModel):
    publishing_role: str = Field("01", alias="PublishingRole")
    publisher_name: str = Field(..., alias="PublisherName")

class Price(OnixBaseModel):
    price_type: PriceType = Field(..., alias="PriceType")
    price_amount: float = Field(..., alias="PriceAmount")
    currency_code: str = Field("UAH", alias="CurrencyCode")

class SupplyDetail(OnixBaseModel):
    supplier: Publisher = Field(..., alias="Supplier") # Reusing Publisher structure for SupplierName
    product_availability: str = Field(..., alias="ProductAvailability")
    price: List[Price] = Field(..., alias="Price")

class RelatedProduct(OnixBaseModel):
    product_relation_code: ProductRelation = Field(..., alias="ProductRelationCode")
    product_identifier: List[ProductIdentifier] = Field(..., alias="ProductIdentifier")

# --- Main Product Model ---

class OnixProduct(OnixBaseModel):
    record_reference: str = Field(..., alias="RecordReference")
    notification_type: NotificationType = Field(..., alias="NotificationType")
    product_identifier: List[ProductIdentifier] = Field(..., alias="ProductIdentifier")
    
    # Block 2: Descriptive Detail
    product_form: ProductForm = Field(..., alias="ProductForm")
    product_form_detail: Optional[List[ProductFormDetail]] = Field(None, alias="ProductFormDetail")
    title_detail: List[TitleDetail] = Field(..., alias="TitleDetail")
    contributor: List[Contributor] = Field(None, alias="Contributor")
    language: List[Language] = Field(None, alias="Language")
    subject: List[Subject] = Field(None, alias="Subject")
    extent: List[Extent] = Field(None, alias="Extent")
    measure: List[Measure] = Field(None, alias="Measure")
    audience_range: List[AudienceRange] = Field(None, alias="AudienceRange")
    collection: List[Collection] = Field(None, alias="Collection")

    # Block 3: Collateral Detail
    text_content: List[TextContent] = Field(None, alias="TextContent")
    supporting_resource: List[SupportingResource] = Field(None, alias="SupportingResource")

    # Block 4: Publishing Detail
    publisher: List[Publisher] = Field(None, alias="Publisher")
    publishing_date: List[PublishingDate] = Field(None, alias="PublishingDate")
    
    # Block 5: Related Material
    related_product: List[RelatedProduct] = Field(default_factory=list, alias="RelatedProduct")
    
    # Block 6: Supply Detail
    supply_detail: List[SupplyDetail] = Field(default_factory=list, alias="SupplyDetail")

    # Extra
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @property
    def primary_isbn(self) -> Optional[str]:
        for pid in self.product_identifier:
            if pid.product_id_type == ProductIdentifierType.ISBN_13:
                return pid.id_value
        return None

    @property
    def distinctive_title(self) -> Optional[str]:
        for title in self.title_detail:
            if title.title_type == TitleType.DISTINCTIVE_TITLE:
                return title.title_element[0].title_text
        return None