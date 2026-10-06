"""Unit tests for deterministic duplicate detection and fingerprinting.

Verifies that variations in casing, punctuation, and whitespace are normalized
and correctly identified as duplicates.
"""

from processing.deduplication import (
    deduplicate_records,
    generate_fingerprint,
    normalize_string_for_fingerprint,
)


class TestDeduplication:
    """Test suite for duplicate detection logic."""

    def test_normalization_rules(self):
        assert normalize_string_for_fingerprint("  Example, Book Title! ") == "example book title"
        assert normalize_string_for_fingerprint("EXAMPLE BOOK TITLE") == "example book title"
        assert normalize_string_for_fingerprint("Example   Book   Title") == "example book title"

    def test_book_title_variations_detected_as_duplicates(self):
        """Assignment requirement:

        The duplicate logic must treat:
        'Example Book Title', 'Example Book Title ', 'EXAMPLE BOOK TITLE'
        as duplicates.
        """
        records = [
            {
                "source": "Books to Scrape",
                "source_url": "https://books.toscrape.com/catalogue/example_1/index.html",
                "name_or_title": "Example Book Title",
                "category": None,
                "price": 20.0,
                "rating": 3,
                "author": None,
                "tags": None,
                "description": None,
                "scraped_at": "2026-10-06T12:00:00Z",
            },
            {
                "source": "Books to Scrape",
                "source_url": "https://books.toscrape.com/catalogue/example_2/index.html",
                "name_or_title": "Example Book Title ",
                "category": None,
                "price": 20.0,
                "rating": 3,
                "author": None,
                "tags": None,
                "description": None,
                "scraped_at": "2026-10-06T12:01:00Z",
            },
            {
                "source": "Books to Scrape",
                "source_url": "https://books.toscrape.com/catalogue/example_3/index.html",
                "name_or_title": "EXAMPLE BOOK TITLE",
                "category": None,
                "price": 20.0,
                "rating": 3,
                "author": None,
                "tags": None,
                "description": None,
                "scraped_at": "2026-10-06T12:02:00Z",
            },
        ]

        unique_records, duplicate_records = deduplicate_records(records)

        assert len(unique_records) == 1
        assert len(duplicate_records) == 2
        assert unique_records[0]["name_or_title"] == "Example Book Title"

    def test_quote_duplicates_by_author_and_prefix(self):
        """Test quote duplicate detection using author + first 50 chars of text."""
        records = [
            {
                "source": "Quotes to Scrape",
                "source_url": "https://quotes.toscrape.com/page/1/",
                "name_or_title": "The world as we have created it is a process of our thinking. It cannot be changed.",
                "category": None,
                "price": None,
                "rating": None,
                "author": "Albert Einstein",
                "tags": "change;thinking",
                "description": None,
                "scraped_at": "2026-10-06T12:00:00Z",
            },
            {
                "source": "Quotes to Scrape",
                "source_url": "https://quotes.toscrape.com/page/2/",
                "name_or_title": "The world as we have created it is a process of our thinking! Differing trailing text.",
                "category": None,
                "price": None,
                "rating": None,
                "author": "albert einstein",
                "tags": "change",
                "description": None,
                "scraped_at": "2026-10-06T12:05:00Z",
            },
        ]

        unique_records, duplicate_records = deduplicate_records(records)
        assert len(unique_records) == 1
        assert len(duplicate_records) == 1

    def test_distinct_records_not_flagged(self):
        records = [
            {
                "source": "Books to Scrape",
                "name_or_title": "Clean Code",
                "source_url": "https://example.com/clean-code",
            },
            {
                "source": "Books to Scrape",
                "name_or_title": "The Pragmatic Programmer",
                "source_url": "https://example.com/pragmatic",
            },
            {
                "source": "Quotes to Scrape",
                "author": "Steve Jobs",
                "name_or_title": "Stay hungry, stay foolish.",
                "source_url": "https://example.com/jobs",
            },
        ]

        unique_records, duplicate_records = deduplicate_records(records)
        assert len(unique_records) == 3
        assert len(duplicate_records) == 0

    def test_deterministic_sha256_fingerprint(self):
        record_a = {"source": "Books to Scrape", "name_or_title": "Python Testing"}
        record_b = {"source": "Books to Scrape", "name_or_title": " PYTHON TESTING "}

        fp_a = generate_fingerprint(record_a)
        fp_b = generate_fingerprint(record_b)

        assert len(fp_a) == 64  # Valid SHA-256 hex string
        assert fp_a == fp_b
