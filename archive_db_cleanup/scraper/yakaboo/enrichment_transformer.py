"""
Yakaboo to Full ONIX 3.0 Transformer (V2)

Цей модуль відповідає за перетворення сирих даних Yakaboo у повну структуру ONIX 3.0 JSON,
визначену в app.schemas.onix_full.

Основні покращення в порівнянні з V1:
- Використання строгих Pydantic моделей
- Повна ієрархія (Product -> DescriptiveDetail -> TitleDetail -> TitleElement)
- Підтримка оригінальних назв та перекладів
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from app.schemas.onix_full import (
    OnixProduct,
    ProductIdentifier,
    ProductIdentifierType,
    TitleDetail,
    TitleType,
    TitleElement,
    Contributor,
    ContributorRole,
    Language,
    LanguageRole,
    Subject,
    SubjectSchemeIdentifier,
    AudienceRange,
    TextContent,
    TextContentType,
    SupportingResource,
    PublishingDate,
    PublishingDateRole,
    Publisher,
    Price,
    PriceType,
    SupplyDetail,
    ProductForm,
    RelatedProduct,
    ProductRelation,
    Measure,
    MeasureType,
    MeasureUnit,
    Extent,
    ExtentType,
)

from app.scraper.yakaboo.helpers import (
    extract_label_value,
    to_list,
    normalize_string,
    safe_int,
    safe_float,
    parse_dimensions,
)
from .extractor import (
    get_binding_code,
    get_lang_code,
    PUBLICATION_TYPE_TO_ONIX,
    ILLUSTRATION_TYPE_TO_ONIX,
    AGE_TO_ONIX
)
from .settings import RECORD_REFERENCE_PREFIX, SOURCE_CODE
from app.configs.yakaboo_mapping import YAKABOO_MAPPING

logger = logging.getLogger(__name__)

def yakaboo_to_onix_v2(data: Dict[str, Any]) -> OnixProduct:
    """
    Transform Yakaboo data to strict OnixProduct model.
    """
    source_id = str(data.get("id"))
    
    # --- 1. Product Identifier ---
    identifiers = []
    
    # Yakaboo ID
    identifiers.append(ProductIdentifier(
        product_id_type=ProductIdentifierType.PROPRIETARY_PRODUCT_ID_SCHEME,
        id_value=source_id
    ))
    
    # ISBN
    isbn_field = YAKABOO_MAPPING["identifiers"]["isbn13"]
    isbn_raw = extract_label_value(data, isbn_field)
    if isbn_raw:
        isbn = str(isbn_raw).replace("-", "").replace(" ", "").strip()
        if len(isbn) == 13:
            identifiers.append(ProductIdentifier(
                product_id_type=ProductIdentifierType.ISBN_13,
                id_value=isbn
            ))
        elif len(isbn) == 10:
            identifiers.append(ProductIdentifier(
                product_id_type=ProductIdentifierType.ISBN_10, # ONIX code 02 = ISBN-10
                id_value=isbn
            ))

    # EAN / Barcode
    barcode_field = YAKABOO_MAPPING["identifiers"]["barcode"]
    barcode = data.get(barcode_field)
    if barcode and barcode != isbn_raw:
        identifiers.append(ProductIdentifier(
            product_id_type=ProductIdentifierType.GTIN_13,
            id_value=str(barcode)
        ))

    # --- 2. Descriptive Detail ---
    
    # Product Form
    # Basic logic: Yakaboo "format" mapping
    # Note: Ideally needs robust mapping from "book_binding_type"
    pf_source = YAKABOO_MAPPING["descriptions"]["product_form_source"]
    binding = data.get(pf_source) or data.get(f"{pf_source}_label")
    product_form = ProductForm.BOOK # Default
    if binding:
        b_str = str(binding).lower()
        if "м'яка" in b_str or "paperback" in b_str:
            product_form = ProductForm.PAPERBACK
        elif "тверда" in b_str or "hardback" in b_str:
            product_form = ProductForm.HARDCOVER
        elif "електронна" in b_str:
            product_form = ProductForm.EBOOK
        elif "аудіо" in b_str:
            product_form = ProductForm.AUDIO

    # Titles
    titles = []
    
    # Distinctive Title
    t_prim = YAKABOO_MAPPING["descriptions"]["title_primary"]
    t_fall = YAKABOO_MAPPING["descriptions"]["title_fallback"]
    name = data.get(t_prim) or data.get(t_fall)
    if name:
        titles.append(TitleDetail(
            title_type=TitleType.DISTINCTIVE_TITLE,
            title_element=[
                TitleElement(
                    title_element_level="01",
                    title_text=normalize_string(name)
                )
            ]
        ))
    
    # Original Title
    t_orig = YAKABOO_MAPPING["descriptions"]["title_original"]
    original_name = extract_label_value(data, t_orig)
    if original_name:
        titles.append(TitleDetail(
            title_type=TitleType.TITLE_IN_ORIGINAL_LANGUAGE,
            title_element=[
                TitleElement(
                    title_element_level="01",
                    title_text=normalize_string(original_name)
                )
            ]
        ))

    # Contributors
    contributors = []
    # Authors
    auth_field = YAKABOO_MAPPING["descriptions"]["contributors_author"]
    # Check for _label suffix logic if needed, but here we assume strict field usage
    # Yakaboo specific: we want 'author_label' usually
    # Mapping says: "contributors_author": "author" but comment says "author_label"
    # Let's trust the code logic: get "author_label" explicitly if the mapping implies it
    # or construct it.
    # To be safe and adhere to config:
    # If config says "author", we look for "author_label" for text.
    # Let's use the field from config as base.
    auth_base = YAKABOO_MAPPING["descriptions"]["contributors_author"]
    author_labels = data.get(f"{auth_base}_label") or [] 
    
    if not isinstance(author_labels, list):
        author_labels = [author_labels]
        
    for auth in author_labels:
        if isinstance(auth, dict) and "label" in auth:
            contributors.append(Contributor(
                contributor_role=[ContributorRole.BY_AUTHOR],
                person_name=normalize_string(auth["label"])
            ))
        elif isinstance(auth, str):
             contributors.append(Contributor(
                contributor_role=[ContributorRole.BY_AUTHOR],
                person_name=normalize_string(auth)
            ))
            
    # Translators
    trans_field = YAKABOO_MAPPING["descriptions"]["contributors_translator"]
    translators = extract_label_value(data, trans_field)
    if translators:
        # Sometimes it's a list or string
        if isinstance(translators, str):
            translators = [translators]
        for trans in translators:
             contributors.append(Contributor(
                contributor_role=[ContributorRole.TRANSLATED_BY],
                person_name=normalize_string(str(trans))
            ))

    # Languages
    languages = []
    lang_field = YAKABOO_MAPPING["descriptions"]["language"]
    lang_val = extract_label_value(data, lang_field)
    lang_code = "ukr" # Default
    if lang_val:
        found_code = get_lang_code(str(lang_val))
        if found_code:
            lang_code = found_code
    
    languages.append(Language(
        language_role=LanguageRole.LANGUAGE_OF_TEXT,
        language_code=lang_code
    ))

    # Subjects
    subjects = []
    # Yakaboo Categories -> Proprietary Subjects with Names
    # Prefer rich "category" list over flat "category_ids"
    sub_rich_field = YAKABOO_MAPPING["descriptions"]["subjects_rich"]
    sub_ids_field = YAKABOO_MAPPING["descriptions"]["subjects_ids"]
    
    cats_rich = data.get(sub_rich_field)
    
    if cats_rich and isinstance(cats_rich, list):
        for c in cats_rich:
            if not isinstance(c, dict): continue
            
            cid = str(c.get("category_id", ""))
            cname = c.get("name")
            
            # Filter garbage
            if cid == "2" or cname == "Default Category":
                continue
                
            subjects.append(Subject(
                subject_scheme_identifier=SubjectSchemeIdentifier.PROPRIETARY_SUBJECT_SCHEME, 
                subject_code=cid,
                subject_heading_text=normalize_string(cname)
            ))
    else:
        # Fallback to IDs if rich data missing
        cats_ids = data.get(sub_ids_field) or []
        for cid in cats_ids:
            if str(cid) == "2": continue
            subjects.append(Subject(
                subject_scheme_identifier=SubjectSchemeIdentifier.KEYWORDS,
                subject_code=str(cid)
            ))

    # Audience
    audience_range = []
    age_field = YAKABOO_MAPPING["descriptions"]["audience_age"]
    age_raw = extract_label_value(data, age_field)
    if age_raw:
        # Try to parse "6-10" or "12+"
        # This is complex, simplified for now
        pass

    # Measures (Dimensions)
    measures = []
    dim_field = YAKABOO_MAPPING["descriptions"]["measure_dimensions"]
    binding_txt = data.get(dim_field) or extract_label_value(data, dim_field)
    if binding_txt:
        dims = parse_dimensions(binding_txt)
        if dims.get("height"):
            measures.append(Measure(
                measure_type=MeasureType.HEIGHT,
                measurement=dims["height"],
                measure_unit_code=MeasureUnit.MILLIMETERS
            ))
        if dims.get("width"):
            measures.append(Measure(
                measure_type=MeasureType.WIDTH,
                measurement=dims["width"],
                measure_unit_code=MeasureUnit.MILLIMETERS
            ))
        if dims.get("thickness"):
            measures.append(Measure(
                measure_type=MeasureType.THICKNESS,
                measurement=dims["thickness"],
                measure_unit_code=MeasureUnit.MILLIMETERS
            ))
            
    # Extents (Page Count)
    extents = []
    pages_field = YAKABOO_MAPPING["descriptions"]["extent_pages"]
    pages_raw = data.get(pages_field) or extract_label_value(data, pages_field)
    if pages_raw:
        val = safe_float(pages_raw)
        if val > 0:
            extents.append(Extent(
                extent_type=ExtentType.MAIN_PAGE_COUNT,
                extent_value=val,
                extent_unit="03" # Pages code
            ))

    # --- 3. Collateral Detail ---
    
            
    
            text_content = []
    
            desc_field = YAKABOO_MAPPING["collateral"]["description_main"]
    
            desc = data.get(desc_field)
    
            if desc:
    
                text_content.append(TextContent(
    
                    text_type=TextContentType.MAIN_DESCRIPTION,
    
                    content_audience="00",
    
                    text=desc
    
                ))
    
        
    
            supporting_resources = []
    
            img_field = YAKABOO_MAPPING["collateral"]["cover_image"]
    
            img_main = data.get(img_field)
    
            if img_main:
    
                supporting_resources.append(SupportingResource(
    
                    resource_content_type="01", # Front Cover
    
                    resource_mode="03", # Image
    
                    resource_version=[{"ResourceLink": img_main}]
    
                ))
    
        
    
            # --- 4. Publishing ---
    
    publishers = []
    pub_field = YAKABOO_MAPPING["publishing"]["publisher_name"]
    pub_name = extract_label_value(data, pub_field)
    if pub_name:
        publishers.append(Publisher(
            publishing_role="01",
            publisher_name=normalize_string(str(pub_name))
        ))

    publishing_dates = []
    year_field = YAKABOO_MAPPING["publishing"]["publishing_year"]
    year = extract_label_value(data, year_field)
    if year:
        publishing_dates.append(PublishingDate(
            publishing_date_role=PublishingDateRole.PUBLICATION_DATE,
            date_format="05", # YYYY
            date_value=str(year)
        ))

    # --- 5. Related Material ---
    related_products = []
    # Similar format links
    rel_field = YAKABOO_MAPPING["related"]["alternative_formats"]
    another = data.get(rel_field) or []
    for rel in to_list(another):
        rid = None
        if isinstance(rel, dict):
            rid = rel.get("id") or rel.get("sku")
        else:
            rid = rel
            
        if rid:
             related_products.append(RelatedProduct(
                 product_relation_code=ProductRelation.ALTERNATIVE_FORMAT,
                 product_identifier=[ProductIdentifier(
                     product_id_type=ProductIdentifierType.PROPRIETARY_PRODUCT_ID_SCHEME,
                     id_value=str(rid)
                 )]
             ))

    # --- 6. Supply ---
    
    price_field = YAKABOO_MAPPING["supply"]["price"]
    old_price_field = YAKABOO_MAPPING["supply"]["old_price"]
    
    price_val = safe_float(data.get(price_field))
    old_price_val = safe_float(data.get(old_price_field))
    
    prices = []
    if price_val:
        prices.append(Price(
            price_type=PriceType.RRP_INC_TAX,
            price_amount=price_val,
            currency_code="UAH"
        ))
        
    supply_detail = []
    if prices:
        stock_field = YAKABOO_MAPPING["supply"]["in_stock"]
        availability = "21" if data.get(stock_field) else "40"
        supply_detail.append(SupplyDetail(
            supplier=Publisher(publishing_role="03", publisher_name="Yakaboo"),
            product_availability=availability,
            price=prices
        ))

    # --- Extra ---
    extra_data = {
        "source_sku": data.get("sku"),
        "url_path": data.get("url_path"),
        "raw_attributes": {k:v for k,v in data.items() if k.startswith("book_")} # Preserve raw attributes
    }

    # Construct Object
    product = OnixProduct(
        record_reference=f"yakaboo_{source_id}",
        notification_type="03",
        product_identifier=identifiers,
        
        # Flattener helpers mapped to DescriptiveDetail
        product_form=product_form,
        title_detail=titles,
        contributor=contributors,
        language=languages,
        subject=subjects,
        audience_range=audience_range,
        measure=measures,
        extent=extents,
        
        text_content=text_content,
        supporting_resource=supporting_resources,
        
        publisher=publishers,
        publishing_date=publishing_dates,
        
        related_product=related_products,
        
        supply_detail=supply_detail,
        
        extra=extra_data
    )
    
    return product
