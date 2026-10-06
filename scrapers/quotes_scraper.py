"""Quotes to Scrape web scraper.

Extracts quotes dynamically across all pages from:
https://quotes.toscrape.com/

Follows dynamic pagination via `li.next > a` without hardcoding page ranges.
Extracts quote text (`span.text`), author (`small.author`), and tags (`a.tag`).
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import urllib.parse

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger("scraper.quotes")


class QuotesScraper(BaseScraper):
    """Scraper for Quotes to Scrape website."""

    START_URL = "https://quotes.toscrape.com/"

    def __init__(
        self,
        base_url: str = START_URL,
        max_pages: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize QuotesScraper.

        Args:
            base_url: The starting URL.
            max_pages: Optional maximum page limit for testing/debugging. If None,
                scrapes dynamically until no next page exists.
            **kwargs: Extra parameters passed to BaseScraper.
        """
        super().__init__(base_url=base_url, **kwargs)
        self.max_pages = max_pages

    def scrape_all(self) -> List[Dict[str, Any]]:
        """Extract all quotes across pages following dynamic pagination.

        Returns:
            List of dictionaries containing raw quote attributes.
        """
        records: List[Dict[str, Any]] = []
        current_url: Optional[str] = self.START_URL
        page_number = 1

        logger.info("Starting Quotes to Scrape extraction from %s", current_url)

        while current_url:
            if self.max_pages is not None and page_number > self.max_pages:
                logger.info(
                    "Reached configured page limit of %d. Stopping Quotes scraper.",
                    self.max_pages,
                )
                break

            logger.info("Scraping Quotes page %d: %s", page_number, current_url)
            soup = self.get_soup(current_url)

            if soup is None:
                logger.error("Failed to retrieve or parse Quotes page %d: %s", page_number, current_url)
                break

            page_records = self._parse_page(soup, current_url)
            records.extend(page_records)
            logger.info(
                "Extracted %d quote items from page %d (total so far: %d)",
                len(page_records),
                page_number,
                len(records),
            )

            # Discover next page dynamically
            next_link_elem = soup.select_one("li.next > a")
            if next_link_elem and next_link_elem.get("href"):
                next_href = next_link_elem["href"]
                current_url = urllib.parse.urljoin(current_url, next_href)
                page_number += 1
            else:
                logger.info(
                    "No next page link found. Quotes pagination finished at page %d.",
                    page_number,
                )
                current_url = None

        logger.info("Completed Quotes scraping. Total records extracted: %d", len(records))
        return records

    def _parse_page(self, soup: Any, current_url: str) -> List[Dict[str, Any]]:
        """Parse all quote elements (`div.quote`) from the page."""
        items: List[Dict[str, Any]] = []
        quote_blocks = soup.select("div.quote")

        if not quote_blocks:
            logger.warning("No quote blocks found on page: %s", current_url)
            return items

        for index, block in enumerate(quote_blocks, start=1):
            try:
                record = self._parse_quote_block(block, current_url)
                if record:
                    items.append(record)
            except Exception as exc:
                logger.error(
                    "Unexpected error parsing quote #%d on %s: %s",
                    index,
                    current_url,
                    exc,
                    exc_info=True,
                )
                # Robustness rule: One failed record must not crash the scraper
                continue

        return items

    def _parse_quote_block(self, block: Any, page_url: str) -> Optional[Dict[str, Any]]:
        """Extract quote details safely from a div.quote block."""
        # Quote text selector: span.text
        text_tag = block.select_one("span.text")
        raw_text = text_tag.get_text() if text_tag else None

        if not raw_text:
            logger.warning("Quote block missing text element on %s", page_url)
            return None

        # Author selector: small.author
        author_tag = block.select_one("small.author")
        author_name = author_tag.get_text(strip=True) if author_tag else None

        # Tags selector: a.tag (0 or more tags)
        tag_tags = block.select("a.tag")
        raw_tags = [t.get_text(strip=True) for t in tag_tags] if tag_tags else []

        # Documented source URL: author profile URL or current page URL
        author_link = block.select_one("a[href*='/author/']")
        if author_link and author_link.get("href"):
            source_url = urllib.parse.urljoin(page_url, author_link["href"])
        else:
            source_url = page_url

        scraped_at = datetime.now(timezone.utc).isoformat()

        return {
            "source": "Quotes to Scrape",
            "source_url": source_url,
            "name_or_title": raw_text,
            "category": None,
            "price": None,
            "rating": None,
            "author": author_name,
            "tags": raw_tags,
            "description": None,
            "scraped_at": scraped_at,
        }
