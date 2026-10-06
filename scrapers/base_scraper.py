"""Base HTTP Scraper module.

Provides a robust, reusable HTTP client built on requests.Session with:
- Connection pooling and session persistence
- Automatic retry logic with exponential backoff for transient errors (429, 500, 502, 503, 504)
- Configurable timeout and polite rate-limiting delays
- UTF-8 response encoding enforcement
- HTML parsing using BeautifulSoup with lxml
- Structured logging and clean exception handling
"""

import logging
import time
from typing import Optional
import urllib.parse

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("scraper.base")


class BaseScraper:
    """Reusable HTTP base scraper providing resilient network requests and parsing."""

    DEFAULT_USER_AGENT = "Educational-Web-Scraping-Assignment/1.0"

    def __init__(
        self,
        base_url: str,
        user_agent: Optional[str] = None,
        timeout: float = 15.0,
        request_delay: float = 0.5,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> None:
        """Initialize the base HTTP scraper.

        Args:
            base_url: The root website URL to scrape.
            user_agent: Custom User-Agent string. If None, default is used.
            timeout: Request timeout in seconds.
            request_delay: Polite delay in seconds between consecutive HTTP requests.
            max_retries: Number of retry attempts for transient server errors.
            backoff_factor: Multiplier for exponential retry backoff sleep.
        """
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.request_delay = request_delay
        self.last_request_time: float = 0.0

        # Initialize persistent session
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent or self.DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

        # Configure robust retry strategy for transient HTTP errors
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.debug(
            "Initialized %s with timeout=%.1fs, delay=%.2fs, max_retries=%d",
            self.__class__.__name__,
            self.timeout,
            self.request_delay,
            max_retries,
        )

    def _apply_rate_limit(self) -> None:
        """Enforce polite rate-limiting between successive HTTP requests."""
        if self.request_delay > 0 and self.last_request_time > 0:
            elapsed = time.time() - self.last_request_time
            sleep_duration = self.request_delay - elapsed
            if sleep_duration > 0:
                logger.debug("Polite delay sleeping for %.3f seconds", sleep_duration)
                time.sleep(sleep_duration)
        self.last_request_time = time.time()

    def get(self, url: str) -> Optional[requests.Response]:
        """Perform an HTTP GET request with retries, timeout, and polite delays.

        Args:
            url: The absolute or relative target URL.

        Returns:
            A requests.Response object if successful, or None on failure.
        """
        full_url = urllib.parse.urljoin(self.base_url, url)
        self._apply_rate_limit()

        try:
            logger.debug("Sending GET request to %s", full_url)
            response = self.session.get(full_url, timeout=self.timeout)

            # Ensure UTF-8 response encoding
            if not response.encoding or response.encoding.lower() in ("iso-8859-1", "ascii"):
                response.encoding = "utf-8"

            if response.status_code >= 400:
                logger.error(
                    "HTTP %d error for URL: %s (Reason: %s)",
                    response.status_code,
                    full_url,
                    response.reason,
                )
                return None

            return response

        except requests.exceptions.Timeout:
            logger.error("Request timed out (%.1fs) fetching URL: %s", self.timeout, full_url)
            return None
        except requests.exceptions.ConnectionError as conn_err:
            logger.error("Connection error fetching URL %s: %s", full_url, conn_err)
            return None
        except requests.exceptions.RequestException as req_err:
            logger.error("Unexpected network failure for %s: %s", full_url, req_err)
            return None

    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch URL and parse HTML content into a BeautifulSoup instance.

        Args:
            url: The absolute or relative target URL.

        Returns:
            BeautifulSoup object parsed with lxml, or None if network/parsing failed.
        """
        response = self.get(url)
        if response is None or not response.text:
            return None

        try:
            return BeautifulSoup(response.text, "lxml")
        except Exception as exc:
            logger.error("Failed to parse HTML for URL %s: %s", url, exc)
            return None

    def close(self) -> None:
        """Close the underlying requests Session."""
        self.session.close()

    def __enter__(self) -> "BaseScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
