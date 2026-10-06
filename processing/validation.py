"""Data validation module.

Validates cleaned records against business rules and schemas.
Returns explicit, granular validation errors without raising uncaught exceptions.
"""

from typing import Any, Dict, List
import urllib.parse

VALID_SOURCES = {"Books to Scrape", "Quotes to Scrape"}


def validate_record(record: Dict[str, Any]) -> List[str]:
    """Validate a single record against schema and business integrity rules.

    Args:
        record: Standardized record dictionary.

    Returns:
        A list of string descriptions for each rule violation found.
        An empty list indicates that the record is valid.
    """
    errors: List[str] = []

    if not isinstance(record, dict):
        return ["Record is not a dictionary"]

    # 1. Source validation
    source = record.get("source")
    if not source or source not in VALID_SOURCES:
        errors.append(f"Invalid or missing source: '{source}'. Must be one of {sorted(VALID_SOURCES)}")

    # 2. Name or Title validation
    name_or_title = record.get("name_or_title")
    if not name_or_title or not str(name_or_title).strip():
        errors.append("Missing or empty name_or_title")

    # 3. Source URL validation
    source_url = record.get("source_url")
    if not source_url or not isinstance(source_url, str):
        errors.append("Missing source_url")
    else:
        try:
            parsed = urllib.parse.urlparse(source_url.strip())
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                errors.append(f"Invalid source_url: '{source_url}'. Must be a valid HTTP/HTTPS URL")
        except Exception:
            errors.append(f"Malformed source_url: '{source_url}'")

    # 4. Price validation (if present)
    price = record.get("price")
    if price is not None and price != "":
        if isinstance(price, (int, float)):
            if price < 0:
                errors.append(f"Price must be non-negative, got: {price}")
        else:
            try:
                numeric_price = float(price)
                if numeric_price < 0:
                    errors.append(f"Price must be non-negative, got: {price}")
            except (ValueError, TypeError):
                errors.append(f"Price must be numeric, got: '{price}'")

    # 5. Rating validation (if present)
    rating = record.get("rating")
    if rating is not None and rating != "":
        if isinstance(rating, int) and not isinstance(rating, bool):
            if not (1 <= rating <= 5):
                errors.append(f"Rating must be an integer between 1 and 5, got: {rating}")
        else:
            try:
                # Disallow floats with non-zero decimal or invalid formats
                f_val = float(rating)
                if not f_val.is_integer() or not (1 <= int(f_val) <= 5):
                    errors.append(f"Rating must be an integer between 1 and 5, got: '{rating}'")
            except (ValueError, TypeError):
                errors.append(f"Rating must be an integer between 1 and 5, got: '{rating}'")

    return errors
