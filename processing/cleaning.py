"""Data cleaning and normalization functions.

Implements granular, reusable cleaning utilities for text, prices,
ratings, tags, and URLs to ensure standardized data hygiene across
all scraped sources.
"""

import re
from typing import Any, Iterable, List, Optional
import urllib.parse


def clean_text(text: Optional[str]) -> str:
    """Normalize whitespace, tabs, newlines, and non-breaking spaces.

    Handles:
    - Leading and trailing spaces
    - Multiple consecutive spaces collapsed into a single space
    - Tabs and newlines
    - Non-breaking spaces (\\xa0)

    Example:
        >>> clean_text("  Hello \\n World\\xa0 ")
        'Hello World'
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Replace non-breaking spaces and zero-width spaces
    text = text.replace("\xa0", " ").replace("\u200b", "")

    # Collapse all whitespace characters (spaces, tabs, newlines) into single space
    return re.sub(r"\s+", " ", text).strip()


def strip_quotes(text: Optional[str]) -> str:
    """Remove surrounding standard and curly quotation marks from text.

    Supported quotation marks:
    - Standard: ", '
    - Curly / Typographic: “, ”, ‘, ’, «, », „, ‟

    Example:
        >>> strip_quotes("“The journey of a thousand miles.”")
        'The journey of a thousand miles.'
    """
    if text is None:
        return ""

    cleaned = clean_text(text)
    quote_chars = "\"\'“”‘’«»„‟"

    # Strip surrounding quotes and whitespace iteratively
    while cleaned and cleaned[0] in quote_chars:
        cleaned = cleaned[1:].strip()
    while cleaned and cleaned[-1] in quote_chars:
        cleaned = cleaned[:-1].strip()

    return cleaned


def clean_price(price_val: Any) -> Optional[float]:
    """Convert raw price strings (e.g., '£51.77', '$12.99') into numeric float.

    Returns:
        float if valid positive price is parsed, else None.
    """
    if price_val is None:
        return None

    if isinstance(price_val, (int, float)):
        return float(price_val)

    text = str(price_val).strip()
    # Match decimal or integer numbers
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match:
        try:
            return round(float(match.group(1)), 2)
        except (ValueError, TypeError):
            return None

    return None


def clean_rating(rating_val: Any) -> Optional[int]:
    """Convert textual rating words ('One'..'Five') or numeric values to integer 1-5.

    Returns:
        Integer between 1 and 5, or None if unrecognized.
    """
    if rating_val is None:
        return None

    word_map = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
    }

    if isinstance(rating_val, int):
        return rating_val if 1 <= rating_val <= 5 else None

    text = str(rating_val).strip().lower()

    if text in word_map:
        return word_map[text]

    # Handle numeric representations like "3" or "3.0"
    try:
        num = int(float(text))
        if 1 <= num <= 5:
            return num
    except (ValueError, TypeError):
        pass

    return None


def clean_tags(tags: Any) -> str:
    """Clean, lowercase, sort alphabetically, and semicolon-join tags.

    Example:
        >>> clean_tags(["Life", "inspiration", "Truth"])
        'inspiration;life;truth'
    """
    if tags is None:
        return ""

    tag_list: List[str] = []
    if isinstance(tags, (list, tuple, set)):
        items = tags
    elif isinstance(tags, str):
        # Split on commas or semicolons if pre-joined
        items = re.split(r"[,;]+", tags)
    else:
        items = [str(tags)]

    for item in items:
        cleaned_item = clean_text(str(item)).lower()
        if cleaned_item:
            tag_list.append(cleaned_item)

    # De-duplicate while sorting consistently
    unique_sorted = sorted(list(set(tag_list)))
    return ";".join(unique_sorted)


def normalize_url(url: Optional[str], base_url: Optional[str] = None) -> str:
    """Ensure URL is absolute and begins with http:// or https://.

    Resolves relative URLs against base_url if provided.
    """
    if not url:
        return ""

    url_str = clean_text(url)
    if not url_str:
        return ""

    if base_url:
        url_str = urllib.parse.urljoin(base_url, url_str)

    # Handle protocol-relative URLs
    if url_str.startswith("//"):
        url_str = "https:" + url_str

    parsed = urllib.parse.urlparse(url_str)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return url_str

    return url_str


def clean_record(raw: dict) -> dict:
    """Apply standardized cleaning to a raw scraped dictionary.

    Produces a dictionary strictly conforming to the common ETL schema.
    """
    source = clean_text(raw.get("source"))

    if source == "Books to Scrape":
        return {
            "source": "Books to Scrape",
            "source_url": normalize_url(raw.get("source_url")),
            "name_or_title": clean_text(raw.get("name_or_title")),
            "category": clean_text(raw.get("category")) or None,
            "price": clean_price(raw.get("price")),
            "rating": clean_rating(raw.get("rating")),
            "author": None,
            "tags": None,
            "description": clean_text(raw.get("description")) or None,
            "scraped_at": raw.get("scraped_at"),
        }

    elif source == "Quotes to Scrape":
        raw_text = raw.get("name_or_title")
        cleaned_quote = strip_quotes(raw_text)

        return {
            "source": "Quotes to Scrape",
            "source_url": normalize_url(raw.get("source_url")),
            "name_or_title": cleaned_quote,
            "category": clean_text(raw.get("category")) or None,
            "price": None,
            "rating": None,
            "author": clean_text(raw.get("author")) or None,
            "tags": clean_tags(raw.get("tags")),
            "description": None,
            "scraped_at": raw.get("scraped_at"),
        }

    # Fallback for generic/unknown records
    return {
        "source": source,
        "source_url": normalize_url(raw.get("source_url")),
        "name_or_title": clean_text(raw.get("name_or_title")),
        "category": clean_text(raw.get("category")) or None,
        "price": clean_price(raw.get("price")),
        "rating": clean_rating(raw.get("rating")),
        "author": clean_text(raw.get("author")) or None,
        "tags": clean_tags(raw.get("tags")) if raw.get("tags") is not None else None,
        "description": clean_text(raw.get("description")) or None,
        "scraped_at": raw.get("scraped_at"),
    }
