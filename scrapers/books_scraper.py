"""Books to Scrape web scraper.

Extracts book listings dynamically across all catalog pages from:
https://books.toscrape.com/

Follows dynamic pagination via `li.next > a` without hardcoding page ranges.
Extracts title (using full title attribute), price, star rating, and book URL.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import urllib.parse

from scrapers.base_scraper import BaseScraper

logger = logging.getLogger("scraper.books")


class BooksScraper(BaseScraper):
    """Scraper for Books to Scrape website."""

    START_URL = "https://books.toscrape.com/"

    def __init__(
        self,
        base_url: str = START_URL,
        scrape_details: bool = False,
        max_pages: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize BooksScraper.

        Args:
            base_url: The starting catalog URL.
            scrape_details: If True, fetches individual book detail pages for
                category and description (slower due to polite delay). Defaults to False.
            max_pages: Optional maximum page limit for testing/debugging. If None,
                scrapes dynamically until no next page exists.
            **kwargs: Extra parameters passed to BaseScraper.
        """
        super().__init__(base_url=base_url, **kwargs)
        self.scrape_details = scrape_details
        self.max_pages = max_pages

    def scrape_all(self) -> List[Dict[str, Any]]:
        """Extract all book records following dynamic pagination.

        Returns:
            List of dictionaries containing raw book attributes.
        """
        records: List[Dict[str, Any]] = []
        current_url: Optional[str] = self.START_URL
        page_number = 1

        logger.info("Starting Books to Scrape extraction from %s", current_url)

        while current_url:
            if self.max_pages is not None and page_number > self.max_pages:
                logger.info(
                    "Reached configured page limit of %d. Stopping Books scraper.",
                    self.max_pages,
                )
                break

            logger.info("Scraping Books page %d: %s", page_number, current_url)
            soup = self.get_soup(current_url)

            if soup is None:
                logger.error("Failed to retrieve or parse Books page %d: %s", page_number, current_url)
                # Avoid infinite loop if a page fails to load
                break

            page_records = self._parse_page(soup, current_url)
            records.extend(page_records)
            logger.info(
                "Extracted %d book items from page %d (total so far: %d)",
                len(page_records),
                page_number,
                len(records),
            )

            # Discover next page link dynamically
            next_link_elem = soup.select_one("li.next > a")
            if next_link_elem and next_link_elem.get("href"):
                next_href = next_link_elem["href"]
                current_url = urllib.parse.urljoin(current_url, next_href)
                page_number += 1
            else:
                logger.info(
                    "No next page link found. Books pagination finished at page %d.",
                    page_number,
                )
                current_url = None

        logger.info("Completed Books scraping. Total records extracted: %d", len(records))
        return records

    def _parse_page(self, soup: Any, current_url: str) -> List[Dict[str, Any]]:
        """Parse all book cards (`article.product_pod`) on a catalog page."""
        items: List[Dict[str, Any]] = []
        pods = soup.select("article.product_pod")

        if not pods:
            logger.warning("No book pods found on page: %s", current_url)
            return items

        for index, pod in enumerate(pods, start=1):
            try:
                record = self._parse_book_pod(pod, current_url)
                if record:
                    items.append(record)
            except Exception as exc:
                logger.error(
                    "Unexpected error parsing book pod #%d on %s: %s",
                    index,
                    current_url,
                    exc,
                    exc_info=True,
                )
                # Robustness rule: One failed record must not crash the entire scraper
                continue

        return items

    def _parse_book_pod(self, pod: Any, page_url: str) -> Optional[Dict[str, Any]]:
        """Extract book details safely from an individual product pod."""
        title_tag = pod.select_one("h3 > a")
        if not title_tag:
            logger.warning("Book pod missing title element on %s", page_url)
            return None

        # Per assignment rules: complete title should come from title attribute
        # because the visible anchor text is truncated with ellipsis.
        raw_title = title_tag.get("title") or title_tag.get_text(strip=True)
        rel_href = title_tag.get("href", "")
        book_url = urllib.parse.urljoin(page_url, rel_href) if rel_href else page_url

        # Price selector: p.price_color
        price_tag = pod.select_one("p.price_color")
        raw_price = price_tag.get_text(strip=True) if price_tag else None

        # Rating selector: p.star-rating
        rating_tag = pod.select_one("p.star-rating")
        raw_rating = None
        if rating_tag:
            # Classes are typically ['star-rating', 'Three']
            classes = rating_tag.get("class", [])
            rating_classes = [c for c in classes if c != "star-rating"]
            if rating_classes:
                raw_rating = rating_classes[0]

        category = None
        description = None

        # Optional detail page fetching if enabled
        if self.scrape_details and book_url:
            detail_cat, detail_desc = self._fetch_book_details(book_url)
            category = detail_cat
            description = detail_desc

        scraped_at = datetime.now(timezone.utc).isoformat()

        return {
            "source": "Books to Scrape",
            "source_url": book_url,
            "name_or_title": raw_title,
            "category": category,
            "price": raw_price,
            "rating": raw_rating,
            "author": None,
            "tags": None,
            "description": description,
            "scraped_at": scraped_at,
        }

    def _fetch_book_details(self, book_url: str) -> tuple[Optional[str], Optional[str]]:
        """Retrieve category and product description from individual book detail page."""
        soup = self.get_soup(book_url)
        if not soup:
            return None, None

        # Category from breadcrumb: ul.breadcrumb > li:nth-child(3) > a
        category = None
        breadcrumb_links = soup.select("ul.breadcrumb > li > a")
        if len(breadcrumb_links) >= 3:
            category = breadcrumb_links[2].get_text(strip=True)

        # Description: #product_description ~ p
        description = None
        desc_header = soup.select_one("#product_description")
        if desc_header:
            desc_tag = desc_header.find_next_sibling("p")
            if desc_tag:
                description = desc_tag.get_text(strip=True)

        return category, description
