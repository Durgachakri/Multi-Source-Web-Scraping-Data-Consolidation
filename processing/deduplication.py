"""Deterministic fingerprint-based duplicate detection module.

Generates SHA-256 cryptographic fingerprints from normalized record attributes
to identify duplicate records across datasets, accounting for casing,
punctuation, and whitespace discrepancies.
"""

import hashlib
import re
from typing import Any, Dict, List, Optional, Set, Tuple


def normalize_string_for_fingerprint(value: Optional[str]) -> str:
    """Normalize a text string for deterministic deduplication comparison.

    Performs:
    1. Null safety
    2. Lowercasing
    3. Punctuation removal
    4. Whitespace collapsing and trimming

    Example:
        >>> normalize_string_for_fingerprint(" Example, Book Title! ")
        'example book title'
    """
    if not value:
        return ""

    text = str(value).lower()
    # Remove all punctuation and symbols (keeping alphanumeric and whitespace)
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse multiple whitespaces and strip boundaries
    return re.sub(r"\s+", " ", text).strip()


def generate_fingerprint(record: Dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 fingerprint for a record.

    Identifying criteria:
    - Books: source + name_or_title
    - Quotes: source + author + first 50 characters of name_or_title

    Args:
        record: Standardized record dictionary.

    Returns:
        64-character hexadecimal SHA-256 digest string.
    """
    source = record.get("source", "")
    norm_source = normalize_string_for_fingerprint(source)

    if source == "Quotes to Scrape":
        norm_author = normalize_string_for_fingerprint(record.get("author"))
        full_norm_title = normalize_string_for_fingerprint(record.get("name_or_title"))
        norm_title_prefix = full_norm_title[:50]
        raw_key = f"{norm_source}|{norm_author}|{norm_title_prefix}"
    else:
        # Default / Books to Scrape
        norm_title = normalize_string_for_fingerprint(record.get("name_or_title"))
        raw_key = f"{norm_source}|{norm_title}"

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def deduplicate_records(
    records: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Identify and segregate duplicate records using deterministic SHA-256 fingerprints.

    Per project requirements, duplicates are removed from the final dataset.

    Args:
        records: List of cleaned, validated record dictionaries.

    Returns:
        Tuple containing:
        - unique_records: First occurrence of each unique record.
        - duplicate_records: Subsequent matching records deemed duplicates.
    """
    seen_fingerprints: Set[str] = set()
    unique_records: List[Dict[str, Any]] = []
    duplicate_records: List[Dict[str, Any]] = []

    for record in records:
        fingerprint = generate_fingerprint(record)
        if fingerprint in seen_fingerprints:
            duplicate_records.append(record)
        else:
            seen_fingerprints.add(fingerprint)
            unique_records.append(record)

    return unique_records, duplicate_records
