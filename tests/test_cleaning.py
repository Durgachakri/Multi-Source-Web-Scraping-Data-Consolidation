"""Unit tests for data cleaning functions.

Does not require network access.
"""

import pytest

from processing.cleaning import (
    clean_price,
    clean_rating,
    clean_record,
    clean_tags,
    clean_text,
    normalize_url,
    strip_quotes,
)


class TestCleanText:
    """Tests for whitespace and string sanitation."""

    def test_whitespace_and_newlines_collapsing(self):
        raw = "  Hello \n\t  World   "
        assert clean_text(raw) == "Hello World"

    def test_non_breaking_spaces(self):
        raw = "Non\xa0breaking\xa0space"
        assert clean_text(raw) == "Non breaking space"

    def test_none_and_empty(self):
        assert clean_text(None) == ""
        assert clean_text("") == ""
        assert clean_text("   ") == ""


class TestStripQuotes:
    """Tests for standard and curly quotation mark removal."""

    def test_standard_double_quotes(self):
        assert strip_quotes('"To be or not to be"') == "To be or not to be"

    def test_standard_single_quotes(self):
        assert strip_quotes("'A journey of a thousand miles'") == "A journey of a thousand miles"

    def test_curly_typographical_quotes(self):
        assert strip_quotes("“The world as we have created it”") == "The world as we have created it"
        assert strip_quotes("‘Single curly quote’") == "Single curly quote"

    def test_nested_whitespace_and_quotes(self):
        assert strip_quotes('  “  Cleaned text  ”  ') == "Cleaned text"

    def test_none_and_empty(self):
        assert strip_quotes(None) == ""
        assert strip_quotes("") == ""


class TestCleanPrice:
    """Tests for monetary price extraction and formatting."""

    def test_gbp_currency_symbol(self):
        assert clean_price("£51.77") == 51.77

    def test_usd_currency_symbol(self):
        assert clean_price("$19.95") == 19.95

    def test_numeric_inputs(self):
        assert clean_price(42.5) == 42.5
        assert clean_price(10) == 10.0

    def test_invalid_and_empty(self):
        assert clean_price("N/A") is None
        assert clean_price("") is None
        assert clean_price(None) is None


class TestCleanRating:
    """Tests for star rating conversion."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("One", 1),
            ("Two", 2),
            ("Three", 3),
            ("Four", 4),
            ("Five", 5),
            ("three", 3),
            ("FIVE", 5),
            ("4", 4),
            (2, 2),
        ],
    )
    def test_valid_ratings(self, raw, expected):
        assert clean_rating(raw) == expected

    @pytest.mark.parametrize("invalid", ["Zero", "Six", "Invalid", "0", 6, -1, None, ""])
    def test_invalid_ratings(self, invalid):
        assert clean_rating(invalid) is None


class TestCleanTags:
    """Tests for tag cleaning, lowercasing, sorting, and semicolon joining."""

    def test_list_of_mixed_case_tags(self):
        raw = ["Life", "inspiration", "Truth"]
        assert clean_tags(raw) == "inspiration;life;truth"

    def test_duplicate_and_spaced_tags(self):
        raw = [" python ", "Python", "web ", "web"]
        assert clean_tags(raw) == "python;web"

    def test_string_delimited_tags(self):
        raw = "tech, AI, Python"
        assert clean_tags(raw) == "ai;python;tech"

    def test_empty_and_none(self):
        assert clean_tags([]) == ""
        assert clean_tags(None) == ""
        assert clean_tags("") == ""


class TestNormalizeUrl:
    """Tests for URL normalization and absolute resolution."""

    def test_relative_url_with_base(self):
        base = "https://books.toscrape.com/catalogue/page-2.html"
        rel = "page-3.html"
        assert normalize_url(rel, base_url=base) == "https://books.toscrape.com/catalogue/page-3.html"

    def test_absolute_url_untouched(self):
        url = "https://quotes.toscrape.com/author/Albert-Einstein"
        assert normalize_url(url) == url

    def test_empty_and_none(self):
        assert normalize_url(None) == ""
        assert normalize_url("") == ""


class TestCleanRecord:
    """Tests for end-to-end record cleaning according to source schema."""

    def test_clean_book_record(self):
        raw = {
            "source": "Books to Scrape",
            "source_url": "catalogue/a-light-in-the-attic_1000/index.html",
            "name_or_title": "  A Light in the Attic  \n",
            "category": None,
            "price": "£51.77",
            "rating": "Three",
            "author": None,
            "tags": None,
            "description": None,
            "scraped_at": "2026-10-06T12:00:00Z",
        }
        cleaned = clean_record(raw)
        assert cleaned["source"] == "Books to Scrape"
        assert cleaned["name_or_title"] == "A Light in the Attic"
        assert cleaned["price"] == 51.77
        assert cleaned["rating"] == 3
        assert cleaned["author"] is None
        assert cleaned["tags"] is None

    def test_clean_quote_record(self):
        raw = {
            "source": "Quotes to Scrape",
            "source_url": "https://quotes.toscrape.com/page/1/",
            "name_or_title": "“The world is beautiful.”",
            "category": None,
            "price": None,
            "rating": None,
            "author": "  Albert Einstein  ",
            "tags": ["World", "beauty"],
            "description": None,
            "scraped_at": "2026-10-06T12:00:00Z",
        }
        cleaned = clean_record(raw)
        assert cleaned["source"] == "Quotes to Scrape"
        assert cleaned["name_or_title"] == "The world is beautiful."
        assert cleaned["author"] == "Albert Einstein"
        assert cleaned["tags"] == "beauty;world"
        assert cleaned["price"] is None
        assert cleaned["rating"] is None
