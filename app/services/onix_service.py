from lxml import etree
from datetime import datetime
from typing import Optional, List
from app.models.models import Product, Author, Publisher


class OnixXmlGenerator:
    """Service for generating ONIX 3.1 XML messages."""
    
    ONIX_NS = "http://ns.editeur.org/onix/3.1"
    NSMAP = {None: ONIX_NS}
    
    def __init__(self, sender_name: str = "ONIX Book System", sender_email: str = ""):
        self.sender_name = sender_name
        self.sender_email = sender_email
    
    def _create_header(self, parent: etree.Element) -> etree.Element:
        """Create ONIX Header block."""
        header = etree.SubElement(parent, "Header")
        
        sender = etree.SubElement(header, "Sender")
        etree.SubElement(sender, "SenderName").text = self.sender_name
        if self.sender_email:
            etree.SubElement(sender, "EmailAddress").text = self.sender_email
        
        etree.SubElement(header, "SentDateTime").text = datetime.now().strftime("%Y%m%dT%H%M%S")
        etree.SubElement(header, "MessageNote").text = "ONIX 3.1 Export"
        
        return header
    
    def _create_product_identifiers(self, product_elem: etree.Element, isbn: str):
        """Create Block 1: Product Identifiers."""
        prod_id = etree.SubElement(product_elem, "ProductIdentifier")
        etree.SubElement(prod_id, "ProductIDType").text = "15"  # ISBN-13
        etree.SubElement(prod_id, "IDValue").text = isbn
    
    def _create_descriptive_detail(self, product_elem: etree.Element, product: Product, 
                                    authors: List[Author], collection_title: Optional[str] = None):
        """Create Block 2: Descriptive Detail."""
        desc = etree.SubElement(product_elem, "DescriptiveDetail")
        
        # Product Composition
        etree.SubElement(desc, "ProductComposition").text = "00"  # Single-component
        
        # Product Form
        etree.SubElement(desc, "ProductForm").text = product.product_form or "BC"
        
        # Title Detail
        title_detail = etree.SubElement(desc, "TitleDetail")
        etree.SubElement(title_detail, "TitleType").text = "01"  # Distinctive title
        title_elem = etree.SubElement(title_detail, "TitleElement")
        etree.SubElement(title_elem, "TitleElementLevel").text = "01"
        etree.SubElement(title_elem, "TitleText").text = product.title
        
        # Contributors (Authors)
        for i, author in enumerate(authors, 1):
            contrib = etree.SubElement(desc, "Contributor")
            etree.SubElement(contrib, "SequenceNumber").text = str(i)
            etree.SubElement(contrib, "ContributorRole").text = "A01"  # Author
            etree.SubElement(contrib, "PersonName").text = author.full_name
            if author.biography:
                bio = etree.SubElement(contrib, "BiographicalNote")
                bio.text = author.biography
        
        # Collection (if present)
        if collection_title:
            coll = etree.SubElement(desc, "Collection")
            etree.SubElement(coll, "CollectionType").text = "10"  # Publisher collection
            coll_title = etree.SubElement(coll, "TitleDetail")
            etree.SubElement(coll_title, "TitleType").text = "01"
            coll_elem = etree.SubElement(coll_title, "TitleElement")
            etree.SubElement(coll_elem, "TitleElementLevel").text = "02"
            etree.SubElement(coll_elem, "TitleText").text = collection_title
        
        # Language
        lang = etree.SubElement(desc, "Language")
        etree.SubElement(lang, "LanguageRole").text = "01"  # Language of text
        etree.SubElement(lang, "LanguageCode").text = product.language or "ukr"
        
        return desc
    
    def _create_collateral_detail(self, product_elem: etree.Element, onix_json: dict):
        """Create Block 3: Collateral Detail (annotations, covers)."""
        if not onix_json:
            return None
            
        collateral = etree.SubElement(product_elem, "CollateralDetail")
        
        # Text Content (annotations)
        text_contents = onix_json.get("text_content", [])
        for tc in text_contents:
            text_elem = etree.SubElement(collateral, "TextContent")
            etree.SubElement(text_elem, "TextType").text = tc.get("text_type", "03")
            etree.SubElement(text_elem, "ContentAudience").text = tc.get("content_audience", "00")
            text_node = etree.SubElement(text_elem, "Text")
            text_node.text = tc.get("text", "")
        
        # Supporting Resources (covers)
        resources = onix_json.get("supporting_resources", [])
        for res in resources:
            res_elem = etree.SubElement(collateral, "SupportingResource")
            etree.SubElement(res_elem, "ResourceContentType").text = res.get("resource_content_type", "01")
            etree.SubElement(res_elem, "ContentAudience").text = "00"
            etree.SubElement(res_elem, "ResourceMode").text = res.get("resource_mode", "03")
            res_ver = etree.SubElement(res_elem, "ResourceVersion")
            etree.SubElement(res_ver, "ResourceForm").text = "02"  # Downloadable
            etree.SubElement(res_ver, "ResourceLink").text = res.get("resource_link", "")
        
        return collateral
    
    def _create_publishing_detail(self, product_elem: etree.Element, publisher: Optional[Publisher]):
        """Create Block 5: Publishing Detail."""
        pub_detail = etree.SubElement(product_elem, "PublishingDetail")
        
        if publisher:
            pub_elem = etree.SubElement(pub_detail, "Publisher")
            etree.SubElement(pub_elem, "PublishingRole").text = "01"  # Publisher
            etree.SubElement(pub_elem, "PublisherName").text = publisher.name
            if publisher.gln:
                pub_id = etree.SubElement(pub_elem, "PublisherIdentifier")
                etree.SubElement(pub_id, "PublisherIDType").text = "06"  # GLN
                etree.SubElement(pub_id, "IDValue").text = publisher.gln
        
        etree.SubElement(pub_detail, "PublishingStatus").text = "04"  # Active
        
        return pub_detail
    
    def _create_product_supply(self, product_elem: etree.Element, onix_json: dict):
        """Create Block 7: Product Supply (pricing)."""
        prices = onix_json.get("prices", []) if onix_json else []
        if not prices:
            return None
        
        supply = etree.SubElement(product_elem, "ProductSupply")
        supply_detail = etree.SubElement(supply, "SupplyDetail")
        etree.SubElement(supply_detail, "ProductAvailability").text = "20"  # Available
        
        for price_data in prices:
            price = etree.SubElement(supply_detail, "Price")
            etree.SubElement(price, "PriceType").text = price_data.get("price_type", "01")
            etree.SubElement(price, "PriceAmount").text = str(price_data.get("price_amount", 0))
            etree.SubElement(price, "CurrencyCode").text = price_data.get("currency_code", "UAH")
            
            # Tax
            if price_data.get("tax_rate_percent"):
                tax = etree.SubElement(price, "Tax")
                etree.SubElement(tax, "TaxType").text = "01"  # VAT
                etree.SubElement(tax, "TaxRateCode").text = price_data.get("tax_rate_code", "S")
                etree.SubElement(tax, "TaxRatePercent").text = str(price_data.get("tax_rate_percent", 20))
        
        return supply
    
    def generate_product_xml(self, product: Product, authors: List[Author], 
                              publisher: Optional[Publisher] = None,
                              collection_title: Optional[str] = None) -> str:
        """Generate complete ONIX 3.1 XML for a single product."""
        
        root = etree.Element("ONIXMessage", nsmap=self.NSMAP, release="3.1")
        
        # Header
        self._create_header(root)
        
        # Product
        product_elem = etree.SubElement(root, "Product")
        etree.SubElement(product_elem, "RecordReference").text = str(product.id)
        etree.SubElement(product_elem, "NotificationType").text = "03"  # Confirmed
        
        # Block 1: Identifiers
        self._create_product_identifiers(product_elem, product.isbn_13)
        
        # Block 2: Descriptive
        self._create_descriptive_detail(product_elem, product, authors, collection_title)
        
        # Block 3: Collateral
        if product.onix_json:
            self._create_collateral_detail(product_elem, product.onix_json)
        
        # Block 5: Publishing
        self._create_publishing_detail(product_elem, publisher)
        
        # Block 7: Supply
        if product.onix_json:
            self._create_product_supply(product_elem, product.onix_json)
        
        return etree.tostring(root, encoding="unicode", pretty_print=True, xml_declaration=True)
