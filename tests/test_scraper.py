"""
Concept: Scraper Unit Tests

This file contains unit tests for the scraper module, including
the scraper service, transformer, and monitor service.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

# Test data: Sample Vivat product JSON structure
SAMPLE_VIVAT_PRODUCT = {
    "name": "Тестова книга: Пригоди у коді",
    "code": "testova-knyha-pryhody-u-kodi-9786171234567",
    "price": {
        "current": 350.00,
        "old": 420.00
    },
    "description": "Це опис тестової книги про програмування.",
    "images": [
        {"url": "https://vivat.com.ua/images/cover.jpg"},
        {"url": "https://vivat.com.ua/images/back.jpg"}
    ],
    "attributes": [
        {"name": "Автор", "value": "Іван Петренко"},
        {"name": "ISBN", "value": "978-617-123-456-7"},
        {"name": "Кількість сторінок", "value": "256"},
        {"name": "Палітурка", "value": "тверда"}
    ],
    "reviews": [
        {
            "text": "Чудова книга для початківців!",
            "rating": 5,
            "author": "Олена"
        }
    ]
}

SAMPLE_NEXT_DATA = {
    "props": {
        "pageProps": {
            "product": SAMPLE_VIVAT_PRODUCT
        }
    },
    "page": "/product/[slug]",
    "query": {"slug": "testova-knyha"},
    "buildId": "abc123"
}

SAMPLE_HTML = f'''
<!DOCTYPE html>
<html>
<head><title>Test Product</title></head>
<body>
<script id="__NEXT_DATA__" type="application/json">
{json.dumps(SAMPLE_NEXT_DATA)}
</script>
</body>
</html>
'''

SAMPLE_SITEMAP = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://vivat.com.ua/knyha-test-1</loc>
        <lastmod>2025-12-20</lastmod>
    </url>
    <url>
        <loc>https://vivat.com.ua/knyha-test-2</loc>
        <lastmod>2025-12-21</lastmod>
    </url>
    <url>
        <loc>https://vivat.com.ua/category/fiction</loc>
        <lastmod>2025-12-19</lastmod>
    </url>
</urlset>
'''


class TestScraperService:
    """Tests for ScraperService."""
    
    def test_extract_next_data(self):
        """Test extraction of __NEXT_DATA__ from HTML."""
        from app.scraper.scraper_service import ScraperService
        
        scraper = ScraperService()
        result = scraper.extract_next_data(SAMPLE_HTML)
        
        assert result is not None
        assert "props" in result
        assert "pageProps" in result["props"]
        assert "product" in result["props"]["pageProps"]
    
    def test_extract_next_data_not_found(self):
        """Test extraction when __NEXT_DATA__ is missing."""
        from app.scraper.scraper_service import ScraperService
        
        scraper = ScraperService()
        result = scraper.extract_next_data("<html><body>No data here</body></html>")
        
        assert result is None
    
    def test_extract_product_data(self):
        """Test extraction of product data from Next.js structure."""
        from app.scraper.scraper_service import ScraperService
        
        scraper = ScraperService()
        result = scraper.extract_product_data(SAMPLE_NEXT_DATA)
        
        assert result is not None
        assert result["name"] == "Тестова книга: Пригоди у коді"
    
    def test_extract_images(self):
        """Test extraction of image URLs."""
        from app.scraper.scraper_service import ScraperService
        
        scraper = ScraperService()
        images = scraper.extract_images(SAMPLE_VIVAT_PRODUCT)
        
        assert len(images) == 2
        assert "https://vivat.com.ua/images/cover.jpg" in images
    
    def test_extract_reviews(self):
        """Test extraction of user reviews."""
        from app.scraper.scraper_service import ScraperService
        
        scraper = ScraperService()
        reviews = scraper.extract_reviews(SAMPLE_VIVAT_PRODUCT)
        
        assert len(reviews) == 1
        assert reviews[0]["text"] == "Чудова книга для початківців!"
        assert reviews[0]["rating"] == 5


class TestVivatTransformer:
    """Tests for VivatTransformer."""
    
    def test_extract_isbn(self):
        """Test ISBN extraction and cleaning."""
        from app.scraper.transformer import VivatTransformer
        
        transformer = VivatTransformer()
        isbn = transformer.extract_isbn(SAMPLE_VIVAT_PRODUCT)
        
        assert isbn == "9786171234567"
    
    def test_extract_authors(self):
        """Test author name extraction."""
        from app.scraper.transformer import VivatTransformer
        
        transformer = VivatTransformer()
        authors = transformer.extract_authors(SAMPLE_VIVAT_PRODUCT)
        
        assert len(authors) == 1
        assert "Іван Петренко" in authors
    
    def test_extract_price(self):
        """Test price extraction."""
        from app.scraper.transformer import VivatTransformer
        
        transformer = VivatTransformer()
        price = transformer.extract_price(SAMPLE_VIVAT_PRODUCT)
        
        assert price is not None
        assert price.price_amount == 350.00
        assert price.currency_code == "UAH"
    
    def test_extract_product_form(self):
        """Test binding type to ONIX code mapping."""
        from app.scraper.transformer import VivatTransformer
        
        transformer = VivatTransformer()
        form = transformer.extract_product_form(SAMPLE_VIVAT_PRODUCT)
        
        assert form == "BB"  # Hardback
    
    def test_transform_full_product(self):
        """Test full transformation pipeline."""
        from app.scraper.transformer import VivatTransformer
        from app.scraper.scraper_service import ScrapedProduct
        
        transformer = VivatTransformer()
        
        scraped = ScrapedProduct(
            raw_json=SAMPLE_VIVAT_PRODUCT,
            source_url="https://vivat.com.ua/test-product",
            images=["https://vivat.com.ua/images/cover.jpg"],
            sample_url=None
        )
        scraped.raw_json["_extracted_reviews"] = [
            {"text": "Great book!", "rating": 5, "author": "User"}
        ]
        
        result = transformer.transform(scraped)
        
        assert result.title == "Тестова книга: Пригоди у коді"
        assert result.isbn_13 == "9786171234567"
        assert result.product_form == "BB"
        assert result.language == "ukr"
        assert result.onix_json is not None
        assert result.onix_json.prices is not None
        assert len(result.onix_json.prices) == 1
        assert result.onix_json.supporting_resources is not None


class TestMonitorService:
    """Tests for MonitorService."""
    
    def test_parse_sitemap(self):
        """Test sitemap XML parsing."""
        from app.scraper.monitor_service import MonitorService
        
        monitor = MonitorService()
        entries = monitor.parse_sitemap(SAMPLE_SITEMAP)
        
        assert len(entries) == 3
        assert entries[0].url == "https://vivat.com.ua/knyha-test-1"
    
    def test_filter_product_urls(self):
        """Test filtering of product URLs."""
        from app.scraper.monitor_service import MonitorService
        
        monitor = MonitorService()
        entries = monitor.parse_sitemap(SAMPLE_SITEMAP)
        products = monitor.filter_product_urls(entries)
        
        # Only URLs containing "/knyha-" should be included
        assert len(products) == 2
        assert all("/knyha-" in p.url for p in products)
    
    def test_find_new_urls(self):
        """Test detection of new URLs."""
        from app.scraper.monitor_service import MonitorService, SitemapEntry
        
        monitor = MonitorService()
        
        # Add one known URL
        monitor._known_urls.add("https://vivat.com.ua/knyha-test-1")
        
        entries = [
            SitemapEntry(url="https://vivat.com.ua/knyha-test-1"),
            SitemapEntry(url="https://vivat.com.ua/knyha-test-2"),
        ]
        
        new_urls = monitor.find_new_urls(entries)
        
        assert len(new_urls) == 1
        assert new_urls[0] == "https://vivat.com.ua/knyha-test-2"


# Run with: pytest tests/test_scraper.py -v
