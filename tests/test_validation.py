"""Unit tests for record validation rules.

Validates schema compliance, URL formats, numeric prices, and rating boundaries
without requiring network access.
"""

import pytest

from processing.validation import validate_record


class TestValidation:
    """Test suite for validate_record function."""

    @pytest.fixture
    def valid_book_record(self):
        return {
            "source": "Books to Scrape",
            "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            "name_or_title": "A Light in the Attic",
            "category": "Poetry",
            "price": 51.77,
            "rating": 3,
            "author": None,
            "tags": None,
            "description": "It's hard to be a poet...",
            "scraped_at": "2026-10-06T12:00:00Z",
        }

    @pytest.fixture
    def valid_quote_record(self):
        return {
            "source": "Quotes to Scrape",
            "source_url": "https://quotes.toscrape.com/author/Albert-Einstein",
            "name_or_title": "The world as we have created it is a process of our thinking.",
            "category": None,
            "price": None,
            "rating": None,
            "author": "Albert Einstein",
            "tags": "change;thinking;world",
            "description": None,
            "scraped_at": "2026-10-06T12:00:00Z",
        }

    def test_valid_book_passes_validation(self, valid_book_record):
        errors = validate_record(valid_book_record)
        assert errors == []

    def test_valid_quote_passes_validation(self, valid_quote_record):
        errors = validate_record(valid_quote_record)
        assert errors == []

    def test_missing_name_or_title(self, valid_book_record):
        valid_book_record["name_or_title"] = ""
        errors = validate_record(valid_book_record)
        assert any("Missing or empty name_or_title" in err for err in errors)

        valid_book_record["name_or_title"] = None
        errors = validate_record(valid_book_record)
        assert any("Missing or empty name_or_title" in err for err in errors)

    def test_invalid_source(self, valid_book_record):
        valid_book_record["source"] = "Unknown Scraper Source"
        errors = validate_record(valid_book_record)
        assert any("Invalid or missing source" in err for err in errors)

    def test_invalid_url(self, valid_book_record):
        valid_book_record["source_url"] = "not_a_valid_url"
        errors = validate_record(valid_book_record)
        assert any("Invalid source_url" in err for err in errors)

        valid_book_record["source_url"] = "ftp://ftp.example.com/resource"
        errors = validate_record(valid_book_record)
        assert any("Invalid source_url" in err for err in errors)

    def test_invalid_price_negative(self, valid_book_record):
        valid_book_record["price"] = -10.50
        errors = validate_record(valid_book_record)
        assert any("Price must be non-negative" in err for err in errors)

    def test_invalid_price_non_numeric(self, valid_book_record):
        valid_book_record["price"] = "fifty dollars"
        errors = validate_record(valid_book_record)
        assert any("Price must be numeric" in err for err in errors)

    def test_valid_zero_price(self, valid_book_record):
        valid_book_record["price"] = 0.0
        errors = validate_record(valid_book_record)
        assert errors == []

    def test_invalid_rating_out_of_bounds(self, valid_book_record):
        valid_book_record["rating"] = 0
        errors = validate_record(valid_book_record)
        assert any("Rating must be an integer between 1 and 5" in err for err in errors)

        valid_book_record["rating"] = 6
        errors = validate_record(valid_book_record)
        assert any("Rating must be an integer between 1 and 5" in err for err in errors)

    def test_invalid_rating_float(self, valid_book_record):
        valid_book_record["rating"] = 3.5
        errors = validate_record(valid_book_record)
        assert any("Rating must be an integer between 1 and 5" in err for err in errors)

    def test_non_dict_record(self):
        errors = validate_record(["not", "a", "dict"])
        assert "Record is not a dictionary" in errors
