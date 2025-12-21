"""
Concept: Scraper Service

This file fetches HTML from target websites and extracts structured JSON data
from Next.js applications. It handles the low-level HTTP requests and parsing
of the `__NEXT_DATA__` script tag that contains pre-rendered product data.
"""

import httpx
import json
import re
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ScrapedProduct:
    """Raw product data extracted from a website before transformation."""
    raw_json: Dict[str, Any]
    source_url: str
    images: list[str]
    sample_url: Optional[str] = None


class ScraperService:
    """Service for fetching and parsing product pages from target websites."""
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    def __init__(self, timeout: float = 30.0, rate_limit_delay: float = 1.0):
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def fetch_page(self, url: str) -> str:
        """Fetch raw HTML from a URL."""
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        return response.text
    
    def extract_next_data(self, html: str) -> Optional[Dict[str, Any]]:
        """
        Extract the __NEXT_DATA__ JSON from a Next.js page.
        
        Returns the parsed JSON or None if not found.
        """
        soup = BeautifulSoup(html, "html.parser")
        script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
        
        if not script_tag or not script_tag.string:
            return None
        
        try:
            return json.loads(script_tag.string)
        except json.JSONDecodeError:
            return None
    
    def extract_product_data(self, next_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Navigate the Next.js data structure to find product information.
        
        Expected path: props.pageProps.product
        """
        try:
            return next_data.get("props", {}).get("pageProps", {}).get("product")
        except (KeyError, TypeError):
            return None
    
    def extract_images(self, product_data: Dict[str, Any]) -> list[str]:
        """
        Extract all image URLs from product data.
        
        Looks for common image patterns in the JSON structure.
        """
        images = []
        
        # SlideShow / Gallery (Vivat structure)
        for gallery_key in ["slideShow", "gallery", "images"]:
            if gallery_key in product_data and isinstance(product_data[gallery_key], list):
                for item in product_data[gallery_key]:
                    if isinstance(item, dict):
                         # Vivat uses "value" for image URL in slideShow
                         url = item.get("value", item.get("url", item.get("src", "")))
                         if url:
                             images.append(url)
                    elif isinstance(item, str):
                        images.append(item)

        # Main image
        if "image" in product_data:
            img = product_data["image"]
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict) and "url" in img:
                images.append(img["url"])
        
        # Cover image (common in book data)
        if "cover" in product_data:
            cover = product_data["cover"]
            if isinstance(cover, str):
                images.append(cover)
            elif isinstance(cover, dict) and "url" in cover:
                images.append(cover["url"])
        
        return list(set(images))  # Remove duplicates
    
    def extract_sample_url(self, product_data: Dict[str, Any], html: str) -> Optional[str]:
        """
        Extract sample/fragment PDF URL if available.
        
        Looks for "Уривок" (fragment) or sample links.
        """
        # Check in product JSON
        if "sample" in product_data:
            return product_data["sample"]
        
        if "fragment" in product_data:
            return product_data["fragment"]
        
        if "uryvok" in product_data:
            return product_data["uryvok"]
        
        # Check in HTML for sample links
        soup = BeautifulSoup(html, "html.parser")
        
        # Look for links containing "uryvok", "sample", or "fragment"
        sample_patterns = [
            r"уривок",
            r"uryvok",
            r"sample",
            r"fragment",
            r"\.pdf"
        ]
        
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            link_text = link.get_text().lower()
            
            for pattern in sample_patterns:
                if re.search(pattern, href, re.IGNORECASE) or \
                   re.search(pattern, link_text, re.IGNORECASE):
                    return href
        
        return None
    
    def extract_reviews(self, product_data: Dict[str, Any]) -> list[Dict[str, Any]]:
        """
        Extract user reviews from product data.
        
        Returns a list of review dictionaries with text and rating.
        """
        reviews = []
        
        # Check common review keys
        review_keys = ["reviews", "comments", "feedback", "opinions"]
        
        for key in review_keys:
            if key in product_data and isinstance(product_data[key], list):
                for review in product_data[key]:
                    if isinstance(review, dict):
                        reviews.append({
                            "text": review.get("text", review.get("comment", review.get("body", ""))),
                            "rating": review.get("rating", review.get("score", None)),
                            "author": review.get("author", review.get("name", review.get("user", "Анонім"))),
                            "date": review.get("date", review.get("created_at", None))
                        })
        
        return reviews
    
    async def scrape_product(self, url: str) -> ScrapedProduct:
        """
        Full scraping pipeline for a product URL.
        
        1. Fetch HTML
        2. Extract __NEXT_DATA__ JSON
        3. Parse product data
        4. Extract images, samples, reviews
        
        Returns a ScrapedProduct with all extracted data.
        """
        html = await self.fetch_page(url)
        
        next_data = self.extract_next_data(html)
        if not next_data:
            raise ValueError(f"Не вдалося знайти __NEXT_DATA__ на сторінці: {url}")
        
        product_data = self.extract_product_data(next_data)
        if not product_data:
            raise ValueError(f"Не вдалося знайти дані про товар: {url}")
        
        images = self.extract_images(product_data)
        sample_url = self.extract_sample_url(product_data, html)
        
        # Add reviews to product data for transformer
        product_data["_extracted_reviews"] = self.extract_reviews(product_data)
        
        return ScrapedProduct(
            raw_json=product_data,
            source_url=url,
            images=images,
            sample_url=sample_url
        )
