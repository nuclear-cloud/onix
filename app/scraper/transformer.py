"""
Concept: Data Transformer

This file transforms raw scraped data from external websites into our
ONIX-compliant internal ProductCreate schema. It acts as the "bridge"
between messy external data and our clean, standardized database model.
"""

import re
import hashlib
import json
from typing import Optional, List, Dict, Any
from app.schemas.schemas import (
    ProductCreate, ProductAuthorBase, OnixJson,
    TextContent, SupportingResource, Price,
    Subject, Extent, Measure, SupplyDetail,
    Contributor, TitleDetail, CollectionDetail
)
from app.scraper.scraper_service import ScrapedProduct


class VivatTransformer:
    """
    Transforms Vivat.com.ua product data into ProductCreate schema.
    
    This class handles the specific mapping logic for the Vivat website,
    converting their JSON structure to our ONIX-compliant format.
    """
    
    # Vivat attribute name mappings (Ukrainian)
    AUTHOR_KEYS = ["Автор", "Автори", "Author", "Authors"]
    ISBN_KEYS = ["ISBN", "isbn", "isbn_13", "ISBN-13"]
    PAGES_KEYS = ["Кількість сторінок", "Сторінок", "Pages", "Обсяг"]
    BINDING_KEYS = ["Палітурка", "Обкладинка", "Binding", "Cover"]
    FORMAT_KEYS = ["Формат", "Format", "Розмір", "Габарити"]
    WEIGHT_KEYS = ["Вага", "Weight"]
    
    # New detailed keys
    ORIGINAL_TITLE_KEYS = ["Оригінальна назва", "Original Title"]
    YEAR_KEYS = ["Рік видання", "Year"]
    SERIES_KEYS = ["Серія", "Series"]
    TRANSLATOR_KEYS = ["Перекладач", "Translator"]
    ILLUSTRATOR_KEYS = ["Ілюстратор", "Illustrator"]
    
    # ONIX Product Form codes
    BINDING_TO_ONIX = {
        "тверда": "BB",      # Hardback
        "м'яка": "BC",       # Paperback
        "мягка": "BC",       # Paperback (alternate spelling)
        "інтегральна": "BC", # Integral (treat as paperback)
        "hardcover": "BB",
        "paperback": "BC",
    }
    
    def __init__(self):
        self._author_cache: Dict[str, str] = {}  # name -> id placeholder
    
    def extract_attribute(self, product_data: Dict[str, Any], keys: List[str]) -> Optional[str]:
        """
        Extract an attribute value by trying multiple possible keys.
        """
        # Try direct keys first
        for key in keys:
            if key in product_data:
                return str(product_data[key])
        
        # Try in attributes/allCharacteristics array (common Vivat structure)
        # Structure is: {"label": "LabelName", "value": [{"text": "Value"}]}
        attributes = product_data.get("allCharacteristics", product_data.get("attributes", []))
        if isinstance(attributes, list):
            for attr in attributes:
                if isinstance(attr, dict):
                    # Check label/name/title
                    attr_name = attr.get("label", attr.get("name", attr.get("title", "")))
                    for key in keys:
                        if key.lower() in attr_name.lower():
                            # Extract value
                            val = attr.get("value", attr.get("text", ""))
                            if isinstance(val, list) and len(val) > 0:
                                # Nested list of values (e.g. [{"text": "Value"}])
                                first_val = val[0]
                                if isinstance(first_val, dict):
                                    return str(first_val.get("text", first_val.get("value", "")))
                                return str(first_val)
                            elif isinstance(val, dict):
                                return str(val.get("text", val.get("value", "")))
                            return str(val)
        
        # Try in characteristics
        characteristics = product_data.get("characteristics", {})
        if isinstance(characteristics, dict):
            for key in keys:
                if key in characteristics:
                    return str(characteristics[key])
        
        return None
    
    def extract_isbn(self, product_data: Dict[str, Any]) -> Optional[str]:
        """Extract and validate ISBN-13 from product data."""
        raw_isbn = self.extract_attribute(product_data, self.ISBN_KEYS)
        
        if not raw_isbn:
            # Try code field (sometimes used as ISBN)
            code = product_data.get("code", product_data.get("sku", ""))
            if code and len(re.sub(r"[^0-9]", "", str(code))) == 13:
                raw_isbn = str(code)
        
        if not raw_isbn:
            return None
        
        clean_isbn = re.sub(r"[^0-9]", "", raw_isbn)
        
        if len(clean_isbn) == 13:
            return clean_isbn
        elif len(clean_isbn) == 10:
            return f"978{clean_isbn[:9]}"
        
        return None
    
    def extract_authors(self, product_data: Dict[str, Any]) -> List[str]:
        """Extract author names from product data."""
        raw_authors = self.extract_attribute(product_data, self.AUTHOR_KEYS)
        
        if not raw_authors:
            return []
        
        separators = [";", ",", " та ", " і ", " and ", " & "]
        authors = [raw_authors]
        
        for sep in separators:
            new_authors = []
            for author in authors:
                new_authors.extend(author.split(sep))
            authors = new_authors
        
        return [a.strip() for a in authors if a.strip()]
    
    def extract_titles(self, product_data: Dict[str, Any]) -> List[TitleDetail]:
        """Extract different types of titles (Distinctive, Original)."""
        titles = []
        
        # Primary title
        main_title = product_data.get("title", product_data.get("name", "Невідома назва"))
        titles.append(TitleDetail(title_type="01", title_text=main_title))
        
        # Original title (Check both labels and englishName top-level key)
        orig_title = self.extract_attribute(product_data, self.ORIGINAL_TITLE_KEYS)
        if not orig_title:
            orig_title = product_data.get("englishName")
            
        if orig_title:
             # Clean up "by Ana Huang" if it exists in the original title field
             orig_title = re.split(r" by | by: ", str(orig_title), flags=re.IGNORECASE)[0]
             titles.append(TitleDetail(title_type="03", title_text=orig_title))
             
        return titles

    def extract_contributors(self, product_data: Dict[str, Any]) -> List[Contributor]:
        """Extract translators, illustrators, etc."""
        contributors = []
        
        # Translators
        translators = self.extract_attribute(product_data, self.TRANSLATOR_KEYS)
        if translators:
            for t in translators.split(","):
                contributors.append(Contributor(
                    contributor_role="B06", # Translator
                    person_name=t.strip()
                ))
        
        # Illustrators
        illustrators = self.extract_attribute(product_data, self.ILLUSTRATOR_KEYS)
        if illustrators:
            for i in illustrators.split(","):
                contributors.append(Contributor(
                    contributor_role="A12", # Illustrator
                    person_name=i.strip()
                ))
                
        return contributors

    def extract_collections(self, product_data: Dict[str, Any]) -> List[CollectionDetail]:
        """Extract book series/collections."""
        collections = []
        series = self.extract_attribute(product_data, self.SERIES_KEYS)
        if series:
            collections.append(CollectionDetail(
                collection_type="10", # Publisher Collection
                title_text=series
            ))
        return collections

    def extract_publishing_date(self, product_data: Dict[str, Any]) -> Optional[str]:
        """Extract publishing year and convert to ONIX YYYYMMDD format."""
        year = self.extract_attribute(product_data, self.YEAR_KEYS)
        if year:
            # Extract digits (usually 4 for year)
            match = re.search(r"\b(20|19)\d{2}\b", year)
            if match:
                # Return start of year YYYY0101
                return f"{match.group(0)}0101"
        return None

    def extract_price(self, product_data: Dict[str, Any]) -> Optional[Price]:
        """Extract price information from product data."""
        price_value = None
        
        if "price" in product_data:
            price_info = product_data["price"]
            if isinstance(price_info, (int, float)):
                price_value = float(price_info)
            elif isinstance(price_info, dict):
                price_value = price_info.get("current", price_info.get("value", price_info.get("amount")))
        
        if "prices" in product_data and isinstance(product_data["prices"], dict):
            prices = product_data["prices"]
            price_value = prices.get("current", prices.get("sale", prices.get("final")))
        
        if price_value is None:
            return None
        
        try:
            return Price(
                price_type="01",  # RRP excluding tax
                price_amount=float(price_value),
                currency_code="UAH",
                tax_rate_percent=20.0
            )
        except (ValueError, TypeError):
            return None
    
    def extract_description(self, product_data: Dict[str, Any]) -> Optional[str]:
        """Extract product description/annotation."""
        # Check specific descriptions from Vivat
        for key in ["bookDescription", "shortDescription", "excerpt", "description", "body", "text"]:
            if key in product_data and product_data[key]:
                return str(product_data[key])
        return None
    
    def extract_product_form(self, product_data: Dict[str, Any]) -> str:
        """Extract and map binding type to ONIX Product Form code."""
        binding = self.extract_attribute(product_data, self.BINDING_KEYS)
        if binding:
            binding_lower = binding.lower()
            for key, code in self.BINDING_TO_ONIX.items():
                if key in binding_lower:
                    return code
        return "BC"  # Default to paperback
    
    def extract_subjects(self, product_data: Dict[str, Any]) -> List[Subject]:
        """Extract subjects/categories."""
        subjects = []
        
        # Breadcrumbs often contain category hierarchy
        if "breadcrumbs" in product_data and isinstance(product_data["breadcrumbs"], list):
            for crumb in product_data["breadcrumbs"]:
                name = crumb.get("label", crumb.get("name", crumb.get("title", "")))
                if name and name.lower() not in ["головна", "книги"]:
                    subjects.append(Subject(
                        subject_scheme_identifier="20",  # Keywords
                        subject_heading_text=name
                    ))
        
        return subjects

    def extract_extent(self, product_data: Dict[str, Any]) -> List[Extent]:
        """Extract page count."""
        pages = self.extract_attribute(product_data, self.PAGES_KEYS)
        if pages:
            # Extract numbers only
            nums = re.findall(r"\d+", pages)
            if nums:
                return [Extent(
                    extent_type="00",  # Main content page count
                    extent_value=float(nums[0]),
                    extent_unit="03"   # Pages
                )]
        return []

    def extract_measures(self, product_data: Dict[str, Any]) -> List[Measure]:
        """Extract dimensions (Height, Width, Thickness) and Weight."""
        measures = []
        
        # Format (e.g., "197 х 127 мм" or "145x215x30")
        fmt = self.extract_attribute(product_data, self.FORMAT_KEYS)
        if fmt:
            # Match up to 3 dimensions separated by x or х
            matches = re.findall(r"(\d+(?:\.\d+)?)", fmt)
            if len(matches) >= 2:
                # Assuming standard W x H or H x W. ONIX uses 01=Height, 02=Width, 03=Thickness
                # Often in books it's H x W. 
                # If we have "197 x 127", 197 is likely Height.
                h, w = float(matches[0]), float(matches[1])
                # Ensure height is the larger one for standard mapping if ambiguous
                if w > h: h, w = w, h
                
                measures.append(Measure(measure_type="01", measurement=h, measure_unit="mm"))
                measures.append(Measure(measure_type="02", measurement=w, measure_unit="mm"))
                
                if len(matches) >= 3:
                    measures.append(Measure(measure_type="03", measurement=float(matches[2]), measure_unit="mm"))
        
        # Weight (e.g., "502 г")
        weight = self.extract_attribute(product_data, self.WEIGHT_KEYS)
        if weight:
             match = re.search(r"(\d+(?:\.\d+)?)", weight)
             if match:
                 measures.append(Measure(measure_type="08", measurement=float(match.group(1)), measure_unit="gr"))
        
        return measures

    def extract_supply(self, product_data: Dict[str, Any], price: Optional[Price]) -> List[SupplyDetail]:
        """Extract availability status."""
        is_available = True
        
        if "stockLevel" in product_data:
            level = product_data["stockLevel"]
            if isinstance(level, (int, float)):
                is_available = level > 0
            elif isinstance(level, str):
                is_available = "in" in level.lower() or "є" in level.lower()
        
        elif "status" in product_data:
            status = str(product_data["status"]).lower()
            if "out" in status or "нема" in status:
                is_available = False
        
        availability_code = "21" if is_available else "40" # 21=In Stock, 40=Not available
            
        return [SupplyDetail(
            supplier_name="Vivat",
            product_availability=availability_code,
            prices=[price] if price else None
        )]

    def build_supporting_resources(
        self, 
        images: List[str], 
        sample_url: Optional[str]
    ) -> List[SupportingResource]:
        """Build ONIX SupportingResource list from images and samples."""
        resources = []
        for i, img_url in enumerate(images):
            # Resource types from ONIX List 158
            resource_type = "01" if i == 0 else "07" # 01=Front Cover, 07=Detail
            resources.append(SupportingResource(
                resource_content_type=resource_type,
                resource_mode="03", # Image
                resource_link=img_url
            ))
        if sample_url:
            resources.append(SupportingResource(
                resource_content_type="15", # Sample content
                resource_mode="06", # PDF or Document
                resource_link=sample_url
            ))
        return resources
    
    def build_text_content(
        self, 
        description: Optional[str],
        reviews: List[Dict[str, Any]],
        author_bio: Optional[str] = None
    ) -> List[TextContent]:
        """Build ONIX TextContent list."""
        content = []
        if description:
            content.append(TextContent(
                text_type="03", # Description
                content_audience="00",
                text=description
            ))
        
        if author_bio:
            content.append(TextContent(
                text_type="12", # Author Bio
                content_audience="00",
                text=author_bio
            ))

        for review in reviews[:5]:
            review_text = review.get("text", "")
            if review_text:
                author = review.get("author", "Читач")
                rating = review.get("rating")
                formatted_review = f"«{review_text}»"
                if rating:
                    formatted_review += f" — {author} ({rating}/5)"
                else:
                    formatted_review += f" — {author}"
                content.append(TextContent(
                    text_type="06", # Review
                    content_audience="00",
                    text=formatted_review
                ))
        return content
    
    def compute_content_hash(self, product_data: Dict[str, Any]) -> str:
        """Compute a hash of the product data for change detection."""
        hash_data = {
            "title": product_data.get("title", product_data.get("name", "")),
            "price": str(product_data.get("price", "")),
            "description": self.extract_description(product_data) or "",
        }
        json_str = json.dumps(hash_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]
    
    def transform(self, scraped: ScrapedProduct) -> ProductCreate:
        """Transform a ScrapedProduct into a ProductCreate schema."""
        product_data = scraped.raw_json
        
        title_details = self.extract_titles(product_data)
        primary_title = title_details[0].title_text if title_details else "Невідома назва"
        
        isbn = self.extract_isbn(product_data)
        if not isbn:
            url_hash = int(hashlib.md5(scraped.source_url.encode()).hexdigest(), 16)
            isbn = str(url_hash)[:13].ljust(13, '0')
        
        description = self.extract_description(product_data)
        author_bio = None
        if "aboutAuthor" in product_data and isinstance(product_data["aboutAuthor"], dict):
            author_bio = product_data["aboutAuthor"].get("text")

        reviews = product_data.get("_extracted_reviews", [])
        price = self.extract_price(product_data)
        
        onix_json = OnixJson(
            titles=title_details,
            contributors=self.extract_contributors(product_data),
            collections=self.extract_collections(product_data),
            publishing_date=self.extract_publishing_date(product_data),
            text_content=self.build_text_content(description, reviews, author_bio) or None,
            supporting_resources=self.build_supporting_resources(scraped.images, scraped.sample_url) or None,
            prices=[price] if price else None,
            subjects=self.extract_subjects(product_data),
            extents=self.extract_extent(product_data),
            measures=self.extract_measures(product_data),
            supply_details=self.extract_supply(product_data, price),
            extra={
                "source_url": scraped.source_url,
                "content_hash": self.compute_content_hash(product_data),
                "sku": product_data.get("skuCode"),
                "views": product_data.get("views")
            }
        )
        
        return ProductCreate(
            isbn_13=isbn,
            title=primary_title,
            product_form=self.extract_product_form(product_data),
            language="ukr",
            onix_json=onix_json,
            authors=None 
        )
