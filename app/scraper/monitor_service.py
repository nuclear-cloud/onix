"""
Concept: Monitor Service

This file handles the discovery and change detection for target websites.
It polls sitemaps to find new products and tracks content hashes to detect
when existing products have been updated.
"""

import asyncio
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, List, Dict, Set
from dataclasses import dataclass
import httpx

from app.scraper.scraper_service import ScraperService, ScrapedProduct
from app.scraper.transformer import VivatTransformer


@dataclass
class SitemapEntry:
    """Represents a single entry from a sitemap."""
    url: str
    lastmod: Optional[datetime] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None


@dataclass
class ProductChange:
    """Represents a detected change in a product."""
    url: str
    change_type: str  # "new" or "updated"
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None


class MonitorService:
    """
    Service for monitoring websites for new and updated products.
    
    Uses sitemap polling for discovery and content hashing for change detection.
    """
    
    SITEMAP_URL = "https://vivat.com.ua/sitemap.xml"
    PRODUCT_URL_PATTERN = "/knyha-"  # Vivat product URLs contain this pattern
    
    def __init__(self, scraper: Optional[ScraperService] = None):
        self.scraper = scraper or ScraperService()
        self.transformer = VivatTransformer()
        self._known_hashes: Dict[str, str] = {}  # url -> content_hash
        self._known_urls: Set[str] = set()
    
    async def fetch_sitemap(self, sitemap_url: Optional[str] = None) -> str:
        """Fetch sitemap XML content."""
        url = sitemap_url or self.SITEMAP_URL
        client = await self.scraper._get_client()
        response = await client.get(url)
        response.raise_for_status()
        return response.text
    
    def parse_sitemap(self, xml_content: str) -> List[SitemapEntry]:
        """
        Parse sitemap XML and extract entries.
        
        Handles both regular sitemaps and sitemap indexes.
        """
        entries = []
        
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Помилка парсингу sitemap: {e}")
        
        # Handle XML namespaces
        namespaces = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        
        # Check if this is a sitemap index
        sitemap_refs = root.findall(".//sm:sitemap", namespaces)
        if sitemap_refs:
            # This is an index, return sitemap URLs
            for sitemap in sitemap_refs:
                loc = sitemap.find("sm:loc", namespaces)
                if loc is not None and loc.text:
                    entries.append(SitemapEntry(url=loc.text))
            return entries
        
        # Parse regular sitemap
        for url_elem in root.findall(".//sm:url", namespaces):
            loc = url_elem.find("sm:loc", namespaces)
            if loc is None or not loc.text:
                continue
            
            entry = SitemapEntry(url=loc.text)
            
            # Parse optional fields
            lastmod = url_elem.find("sm:lastmod", namespaces)
            if lastmod is not None and lastmod.text:
                try:
                    # Handle different date formats
                    date_str = lastmod.text
                    if "T" in date_str:
                        entry.lastmod = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        entry.lastmod = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    pass
            
            changefreq = url_elem.find("sm:changefreq", namespaces)
            if changefreq is not None:
                entry.changefreq = changefreq.text
            
            priority = url_elem.find("sm:priority", namespaces)
            if priority is not None and priority.text:
                try:
                    entry.priority = float(priority.text)
                except ValueError:
                    pass
            
            entries.append(entry)
        
        return entries
    
    def filter_product_urls(self, entries: List[SitemapEntry]) -> List[SitemapEntry]:
        """Filter sitemap entries to only include product URLs."""
        return [
            entry for entry in entries
            if self.PRODUCT_URL_PATTERN in entry.url
        ]
    
    async def discover_products(self, sitemap_url: Optional[str] = None) -> List[SitemapEntry]:
        """
        Discover all product URLs from the sitemap.
        
        Handles sitemap indexes by recursively fetching child sitemaps.
        """
        all_products = []
        
        xml_content = await self.fetch_sitemap(sitemap_url)
        entries = self.parse_sitemap(xml_content)
        
        # Check if we need to fetch child sitemaps
        sitemap_entries = [e for e in entries if e.url.endswith(".xml")]
        product_entries = self.filter_product_urls(entries)
        
        all_products.extend(product_entries)
        
        # Recursively fetch child sitemaps
        for sitemap_entry in sitemap_entries:
            try:
                child_products = await self.discover_products(sitemap_entry.url)
                all_products.extend(child_products)
                await asyncio.sleep(0.5)  # Rate limiting
            except Exception:
                continue  # Skip failed sitemaps
        
        return all_products
    
    def find_new_urls(self, product_entries: List[SitemapEntry]) -> List[str]:
        """
        Find URLs that are not in our known set.
        
        Returns list of new URLs.
        """
        new_urls = []
        for entry in product_entries:
            if entry.url not in self._known_urls:
                new_urls.append(entry.url)
        return new_urls
    
    def find_updated_urls(
        self, 
        product_entries: List[SitemapEntry],
        last_check: Optional[datetime] = None
    ) -> List[str]:
        """
        Find URLs that have been modified since last check.
        
        Uses lastmod timestamps from sitemap.
        """
        if last_check is None:
            return []
        
        updated_urls = []
        for entry in product_entries:
            if entry.url in self._known_urls and entry.lastmod:
                if entry.lastmod > last_check:
                    updated_urls.append(entry.url)
        
        return updated_urls
    
    async def check_for_changes(
        self, 
        last_check: Optional[datetime] = None
    ) -> List[ProductChange]:
        """
        Main method to check for new and updated products.
        
        Returns a list of ProductChange objects.
        """
        changes = []
        
        # Discover all products from sitemap
        product_entries = await self.discover_products()
        
        # Find new URLs
        new_urls = self.find_new_urls(product_entries)
        for url in new_urls:
            changes.append(ProductChange(
                url=url,
                change_type="new"
            ))
        
        # Find updated URLs
        updated_urls = self.find_updated_urls(product_entries, last_check)
        for url in updated_urls:
            changes.append(ProductChange(
                url=url,
                change_type="updated",
                old_hash=self._known_hashes.get(url)
            ))
        
        return changes
    
    async def scrape_and_hash(self, url: str) -> tuple[ScrapedProduct, str]:
        """
        Scrape a product and compute its content hash.
        
        Returns (scraped_product, content_hash).
        """
        scraped = await self.scraper.scrape_product(url)
        content_hash = self.transformer.compute_content_hash(scraped.raw_json)
        return scraped, content_hash
    
    def update_known_state(self, url: str, content_hash: str):
        """Update the known state for a URL."""
        self._known_urls.add(url)
        self._known_hashes[url] = content_hash
    
    def load_known_state(self, known_urls: Set[str], known_hashes: Dict[str, str]):
        """Load known state from persistent storage."""
        self._known_urls = known_urls
        self._known_hashes = known_hashes
    
    def export_known_state(self) -> tuple[Set[str], Dict[str, str]]:
        """Export known state for persistent storage."""
        return self._known_urls.copy(), self._known_hashes.copy()


async def run_monitor_cycle(monitor: MonitorService, last_check: Optional[datetime] = None):
    """
    Run a single monitoring cycle.
    
    This is a helper function that can be scheduled with APScheduler or similar.
    """
    print(f"[Monitor] Починаємо перевірку змін...")
    
    changes = await monitor.check_for_changes(last_check)
    
    print(f"[Monitor] Знайдено {len(changes)} змін")
    
    for change in changes:
        print(f"  - [{change.change_type.upper()}] {change.url}")
    
    return changes
