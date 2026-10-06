# Multi-Source Web Scraping & Data Processing ETL Pipeline

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Code Style](https://img.shields.io/badge/code%20style-PEP%208-green.svg)](https://peps.python.org/pep-0008/)
[![Test Suite](https://img.shields.io/badge/tests-pytest-orange.svg)](https://docs.pytest.org/)

A production-grade, beginner-friendly, and fault-tolerant Python ETL (Extract, Transform, Load) data pipeline that scrapes two public practice websites, standardizes heterogeneous data into a unified schema, performs strict data cleaning and validation, detects duplicates via deterministic cryptographic hashing, and persists reconciled outputs.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Assignment Objective](#assignment-objective)
3. [Architecture & Workflow](#architecture--workflow)
4. [Technologies Used & Python Version](#technologies-used--python-version)
5. [Project Structure](#project-structure)
6. [Installation & Setup](#installation--setup)
7. [How to Run](#how-to-run)
8. [Dynamic Pagination Architecture](#dynamic-pagination-architecture)
9. [Scraping Approach (Books & Quotes)](#scraping-approach-books--quotes)
10. [Common Data Model](#common-data-model)
11. [Data Cleaning Strategy](#data-cleaning-strategy)
12. [Validation System](#validation-system)
13. [Deterministic Duplicate Detection](#deterministic-duplicate-detection)
14. [Resilience & Error Handling](#resilience--error-handling)
15. [Logging & Observability](#logging--observability)
16. [Output Artifacts & Metric Reconciliation](#output-artifacts--metric-reconciliation)
17. [Testing](#testing)
18. [Assumptions & Known Limitations](#assumptions--known-limitations)
19. [Interview Q&A Guide](#interview-qa-guide)
20. [AI Usage Summary](#ai-usage-summary)

---

## Project Overview

This project implements an end-to-end multi-source data pipeline that harvests structured data from two distinct public web sources:
1. **Books to Scrape** (`https://books.toscrape.com/`) - A fictitious online bookstore with 50 catalog pages and 1,000 book records.
2. **Quotes to Scrape** (`https://quotes.toscrape.com/`) - A collection of famous quotations spanning 10 paginated pages and 100 quote records.

The pipeline executes through strict sequential stages:
$$\text{Scrape} \longrightarrow \text{Clean} \longrightarrow \text{Validate} \longrightarrow \text{Deduplicate} \longrightarrow \text{Consolidate} \longrightarrow \text{Save Outputs}$$

---

## Assignment Objective

The core goals of this project are:
- Demonstrate resilient web scraping using modern, clean Python standard practices (`requests.Session`, `BeautifulSoup4`, `lxml`).
- Eliminate hardcoded assumptions (such as fixed page counts).
- Maintain complete separation of concerns between extraction, transformation, validation, and storage.
- Guarantee fault isolation: a single malformed item or an entire source downtime will never crash the overall pipeline.
- Implement polite rate limiting and automated exponential backoff retries for transient HTTP errors.
- Deliver comprehensive unit testing and clear documentation suitable for technical evaluation and technical interviews.

---

## Architecture & Workflow

```
+-------------------------------------------------------------------------+
|                              DATA PIPELINE                              |
+-------------------------------------------------------------------------+
       |                                                 |
       v                                                 v
[Books to Scrape]                                [Quotes to Scrape]
   (50 pages)                                       (10 pages)
       |                                                 |
       +-----------------------+-------------------------+
                               |
                               v
                     [1. Scrape (Raw Data)]
         - BaseScraper session pooling
         - 0.5s polite rate-limiting delay
         - Retries on 429, 500, 502, 503, 504
         - Follows 'li.next > a' dynamically
                               |
                               v
                    [2. Clean & Normalize]
         - Whitespace & non-breaking space collapsing
         - Currency stripping (£ / $ -> float)
         - Word rating to int (One..Five -> 1..5)
         - Typographical curly quote stripping
         - Tag lowercasing, sorting, semicolon joining
                               |
                               v
                    [3. Validation Engine]
         - Source membership verification
         - Mandatory non-empty title/name
         - Valid HTTP/HTTPS source URLs
         - Non-negative numeric prices
         - Integer rating bounds [1, 5]
                               |
                               v
                 [4. Deduplication via SHA-256]
         - Normalizes casing, punctuation, and whitespace
         - Composite key: source + identifying fields
         - Cryptographic fingerprinting
         - Excludes duplicates from final dataset
                               |
                               v
                   [5. Consolidation & Output]
         - Fixed 10-column schema ordering
         - output/final_dataset.csv (UTF-8 encoded)
         - output/summary_report.json (Reconciled metrics)
         - logs/scraper.log (Timestamped execution trace)
```

---

## Technologies Used & Python Version

- **Python Version**: Python 3.10 to 3.12 compatible (Tested on Python 3.10.0).
- **Core HTTP**: `requests==2.33.1` with `requests.Session()` connection pooling.
- **HTML Parsing**: `beautifulsoup4==4.14.3` with `lxml==6.0.4` for high-performance C-based parsing.
- **Retry Logic**: `urllib3.util.retry.Retry` with exponential backoff mounted via `HTTPAdapter`.
- **Testing**: `pytest==9.1.1` for offline unit testing.
- **Standard Library Modules**: `hashlib`, `urllib.parse`, `csv`, `json`, `logging`, `argparse`, `datetime`.

*Note: Headless browsers like Selenium or Playwright were intentionally omitted because both target sites render HTML server-side. Using Requests + BeautifulSoup is faster, significantly lighter, and avoids unnecessary dependencies.*

---

## Project Structure

```text
scraping_assignment/
│
├── scrapers/
│   ├── __init__.py           # Package exports for scraper classes
│   ├── base_scraper.py       # Reusable HTTP client, session, retries, delay, lxml soup
│   ├── books_scraper.py      # Books to Scrape catalog extractor with dynamic pagination
│   └── quotes_scraper.py     # Quotes to Scrape extractor with dynamic pagination
│
├── processing/
│   ├── __init__.py           # Package exports for processing functions
│   ├── cleaning.py           # Granular cleaning: text, quotes, prices, ratings, tags, URLs
│   ├── validation.py         # Schema and business rule validators with error categorization
│   └── deduplication.py      # SHA-256 fingerprint generation and duplicate exclusion
│
├── tests/
│   ├── __init__.py           # Tests package initialization
│   ├── conftest.py           # Pytest PYTHONPATH resolution fixture
│   ├── test_cleaning.py      # 29 unit tests covering all cleaning functions
│   ├── test_validation.py    # 11 unit tests for schema constraints & boundary checks
│   └── test_deduplication.py # 5 unit tests for duplicate detection & title variations
│
├── output/                   # Auto-created on runtime
│   ├── final_dataset.csv     # Final cleaned, validated, deduplicated dataset
│   └── summary_report.json   # Comprehensive run audit metrics
│
├── logs/                     # Auto-created on runtime
│   └── scraper.log           # Timestamped execution log
│
├── main.py                   # Master pipeline orchestrator & CLI interface
├── requirements.txt          # Pinned runtime and testing dependencies
├── README.md                 # Project documentation & architectural manual
└── AI_USAGE.md               # Transparent AI disclosure report
```

---

## Installation & Setup

### 1. Clone or Navigate to the Repository
```bash
cd "scraping_assignment"
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## How to Run

### Standard Execution (Scrapes Both Sources Completely)
```bash
python main.py
```
This triggers the complete pipeline:
- Scrapes all 50 pages of Books to Scrape.
- Scrapes all 10 pages of Quotes to Scrape.
- Cleans and standardizes all 1,100 records.
- Validates every record against schema constraints.
- Deduplicates using deterministic SHA-256 fingerprints.
- Generates `output/final_dataset.csv`, `output/summary_report.json`, and `logs/scraper.log`.

### Optional Command-Line Arguments
The pipeline includes configurable CLI options for testing and development:

```bash
# Test run limited to 2 pages per source (fast sanity check)
python main.py --max-pages 2

# Scrape only Books to Scrape
python main.py --source books

# Scrape only Quotes to Scrape
python main.py --source quotes

# Adjust polite request delay (e.g., 0.25 seconds)
python main.py --delay 0.25

# Fetch book detail pages for category and description
python main.py --scrape-details --max-pages 1
```

---

## Dynamic Pagination Architecture

**Never Hardcode Page Ranges:**
Neither scraper relies on loops such as `for page in range(1, 51)`. Real-world websites frequently expand, contract, or re-order catalog listings.

**Implementation Mechanism:**
1. The scraper starts at the source URL (`https://books.toscrape.com/` or `https://quotes.toscrape.com/`).
2. After extracting records from the current page, it queries the DOM for the next button:
   ```python
   next_link_elem = soup.select_one("li.next > a")
   ```
3. If present, the relative target `href` (e.g. `catalogue/page-2.html` or `/page/2/`) is resolved to an absolute URL using:
   ```python
   current_url = urllib.parse.urljoin(current_url, next_link_elem["href"])
   ```
4. When `li.next > a` is absent (the terminal page), `current_url` becomes `None` and the extraction loop terminates organically.

---

## Scraping Approach (Books & Quotes)

### Books to Scrape (`https://books.toscrape.com/`)
- **Book Container**: `article.product_pod`
- **Book Title**: `h3 > a`. The full title is extracted from the `title` HTML attribute (`a.get("title")`) rather than visible inner text, because the visible text is truncated with ellipses on longer titles (e.g., `"A Light in the Attic"` vs `"A Light in the ..."`).
- **Price**: `p.price_color` (e.g. `"£51.77"`).
- **Rating**: `p.star-rating`. The CSS class list is inspected (e.g., `['star-rating', 'Three']`), extracting the rating name.
- **Book URL**: `h3 > a[href]`, resolved absolutely using `urllib.parse.urljoin`.
- **Category & Description**:
  - *Architectural Decision*: By default, category and description are set to `None` for catalog scraping. Scraping 1,000 separate detail pages at a polite 0.5s rate limit would require an additional ~8.5 minutes (500 seconds). If enabled via `--scrape-details`, individual product pages are fetched respecting rate limits. This decision is fully documented in accordance with the assignment guidelines.

### Quotes to Scrape (`https://quotes.toscrape.com/`)
- **Quote Container**: `div.quote`
- **Quote Text**: `span.text` (e.g. `“The world as we have created it...”`).
- **Author**: `small.author` (e.g. `"Albert Einstein"`).
- **Tags**: `a.tag` (zero or more tags extracted as a list of strings).
- **Source URL**: Documented quote author URL or page URL.

---

## Common Data Model

Both disparate sources are normalized into a unified 10-column relational schema in this exact order:

| Column | Type | Books to Scrape | Quotes to Scrape |
| :--- | :--- | :--- | :--- |
| `source` | `str` | `"Books to Scrape"` | `"Quotes to Scrape"` |
| `source_url` | `str` | Canonical Book Page URL | Author URL or Page URL |
| `name_or_title` | `str` | Full Book Title | Cleaned Quote Text |
| `category` | `str \| None` | Category if scraped, else `None` | `None` (empty) |
| `price` | `float \| None`| Numeric price (e.g., `51.77`) | `None` (empty) |
| `rating` | `int \| None` | Integer 1 to 5 (e.g., `3`) | `None` (empty) |
| `author` | `str \| None` | `None` (empty) | Author Name (e.g., `"Albert Einstein"`) |
| `tags` | `str \| None` | `None` (empty) | Semicolon-delimited (e.g., `"change;world"`) |
| `description` | `str \| None`| Description if scraped, else `None` | `None` (empty) |
| `scraped_at` | `str` | ISO-8601 UTC timestamp | ISO-8601 UTC timestamp |

*Integrity Rule: Fake default values such as `price = 0` or `rating = 0` are never inserted for inapplicable fields. Empty fields are represented as `None` in memory and written as empty cells `""` in the CSV.*

---

## Data Cleaning Strategy

All cleaning routines reside in `processing/cleaning.py`:
1. `clean_text()`: Replaces non-breaking spaces (`\xa0`), collapses multiple consecutive whitespace characters, tabs, and newlines into a single space, and strips boundaries.
2. `strip_quotes()`: Strips surrounding double quotes (`"`, `'`) and typographic curly quotes (`“`, `”`, `‘`, `’`, `«`, `»`) from quote text.
3. `clean_price()`: Uses regular expressions to extract decimal and integer values from currency strings (`"£51.77"` $\rightarrow$ `51.77`).
4. `clean_rating()`: Maps English star rating words (`"One"`..`"Five"`) and numeric strings to integers $1 \le n \le 5$.
5. `clean_tags()`: Trims whitespace, lowercases all tags, sorts them alphabetically for deterministic order, and joins them with semicolons (`["Life", "inspiration", "Truth"]` $\rightarrow$ `"inspiration;life;truth"`).
6. `normalize_url()`: Resolves relative URLs to absolute HTTP/HTTPS addresses and normalizes protocol-relative links.

---

## Validation System

Located in `processing/validation.py`, `validate_record()` evaluates every record against business and schema constraints:
- `source`: Must strictly match `"Books to Scrape"` or `"Quotes to Scrape"`.
- `name_or_title`: Must be non-empty and non-whitespace.
- `source_url`: Must parse as a valid HTTP or HTTPS URL with a valid network location (`netloc`).
- `price`: If present, must be numeric and non-negative ($\ge 0.0$).
- `rating`: If present, must be an integer between 1 and 5 inclusive.

Violations return explicit descriptive errors (e.g., `"Rating must be an integer between 1 and 5, got: 6"`). Invalid records are excluded from the output dataset and tallied by reason in `summary_report.json`.

---

## Deterministic Duplicate Detection

Located in `processing/deduplication.py`, deduplication ensures data cleanliness:
1. **Normalization Step**: Lowercases, strips punctuation (`[^\w\s]`), and collapses internal whitespace.
2. **Identifying Keys**:
   - Books: `source + name_or_title`
   - Quotes: `source + author + first 50 characters of name_or_title`
3. **Cryptographic Fingerprint**: The normalized composite key is hashed using **SHA-256**:
   ```python
   raw_key = f"{norm_source}|{norm_title}"
   fingerprint = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
   ```
4. **Duplicate Exclusion**: A hash set tracks seen fingerprints. The first occurrence is preserved in `unique_records`, while subsequent duplicates are isolated in `duplicate_records` and omitted from the final CSV.

*Handled Scenarios*: Variations like `"Example Book Title"`, `"Example Book Title "`, and `"EXAMPLE BOOK TITLE"` produce identical SHA-256 digests and are correctly identified as duplicates.

---

## Resilience & Error Handling

- **Connection Retries**: `urllib3.util.retry.Retry` automatically retries HTTP status codes `429`, `500`, `502`, `503`, and `504` with exponential backoff (`backoff_factor=1.0`).
- **Polite Delays**: `time.sleep(self.request_delay)` enforces a 0.5-second gap between consecutive requests, preventing server throttling.
- **Timeouts**: Every network call specifies an explicit 15.0-second timeout.
- **Source Fault Isolation**: Books and Quotes scrapers run inside independent `try...except` blocks in `main.py`. If one source encounters an unrecoverable failure, the second source continues processing normally.
- **Card-Level Fault Isolation**: An error parsing an individual HTML element skips only that single card and logs a warning without terminating the page crawl.

---

## Logging & Observability

Logging is configured in `main.py` with dual destinations:
1. **Console (`sys.stdout`)**: Real-time terminal progress indicators.
2. **File (`logs/scraper.log`)**: Persistent audit trail.

**Log Levels Applied:**
- `INFO`: Scraper start/finish, page progress, records extracted per page, pipeline transitions, and output file writes.
- `WARNING`: Rejected records with validation failure reasons, duplicate exclusions.
- `ERROR`: HTTP status failures, connection timeouts, or malformed DOM elements.

---

## Output Artifacts & Metric Reconciliation

Upon execution completion, the pipeline outputs two files:

### 1. `output/final_dataset.csv`
A UTF-8 encoded CSV file adhering strictly to the common 10-column schema:
```csv
source,source_url,name_or_title,category,price,rating,author,tags,description,scraped_at
Books to Scrape,https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html,A Light in the Attic,,51.77,3,,,,"2026-10-06T09:30:00Z"
Quotes to Scrape,https://quotes.toscrape.com/author/Albert-Einstein,The world as we have created it is a process of our thinking. It cannot be changed without changing our thinking.,,,,Albert Einstein,change;deep-thoughts;thinking;world,,"2026-10-06T09:30:30Z"
```

### 2. `output/summary_report.json`
A comprehensive JSON document detailing pipeline performance and reconciliation:
```json
{
  "run": {
    "start_time": "2026-10-06T13:35:52.483112+00:00",
    "end_time": "2026-10-06T13:36:27.181837+00:00",
    "duration_seconds": 34.7
  },
  "sources": {
    "Books to Scrape": {
      "raw_records": 1000,
      "cleaned_records": 1000,
      "rejected_records": 0
    },
    "Quotes to Scrape": {
      "raw_records": 100,
      "cleaned_records": 100,
      "rejected_records": 0
    }
  },
  "rejection_reasons": {},
  "duplicates_found": 1,
  "final_record_count": 1099
}
```

### Actual Execution Metrics (Latest Verified Run)

| Metric | Books to Scrape | Quotes to Scrape | Consolidated Total |
| :--- | :---: | :---: | :---: |
| **Raw Records Scraped** | 1,000 | 100 | **1,100** |
| **Cleaned Records** | 1,000 | 100 | **1,100** |
| **Validation Failures (Rejected)** | 0 | 0 | **0** |
| **Duplicates Detected & Excluded** | 1 | 0 | **1** |
| **Final Records Saved to CSV** | 999 | 100 | **1,099** |

**Metric Reconciliation Guarantee:**
$$\text{final\_record\_count} = (\text{raw\_records} - \text{rejected\_records}) - \text{duplicates\_found}$$
$$1099 = (1100 - 0) - 1$$
$$\text{final\_record\_count} = \text{total CSV data rows (excluding header)} = 1099$$

---

## Testing

The test suite runs 100% offline without requiring internet access.

```bash
# Run the entire test suite
python -m pytest tests/

# Run with verbose output
python -m pytest -v tests/
```

### Test Coverage Highlights:
- `tests/test_cleaning.py` (29 tests):
  - Whitespace collapsing, newline removal, `\xa0` handling.
  - Typographic curly quote removal (`“”` and `‘’`).
  - GBP/USD price parsing (`£51.77` $\rightarrow$ `51.77`).
  - Word star rating conversion (`"Three"` $\rightarrow$ `3`).
  - Tag normalization, lowercasing, sorting, and semicolon joining.
  - Relative and protocol-relative URL resolution.
- `tests/test_validation.py` (11 tests):
  - Valid book and quote schema validation.
  - Missing title rejection.
  - Invalid URL schemes (e.g., `ftp://`).
  - Negative and non-numeric price rejection.
  - Out-of-bounds star ratings ($< 1$ or $> 5$).
- `tests/test_deduplication.py` (5 tests):
  - Deduplication across casing, punctuation, and whitespace variations:
    `"Example Book Title"`, `"Example Book Title "`, `"EXAMPLE BOOK TITLE"`.
  - Quote deduplication by author + 50-character title prefix.
  - SHA-256 fingerprint determinism.

---

## Assumptions & Known Limitations

1. **Books Category & Description Extraction**:
   - The Books catalog pages do not expose the book category or full description text.
   - To scrape them would require visiting 1,000 individual product detail pages, adding ~500 seconds (~8.5 minutes) of polite crawling.
   - By default, `category` and `description` are left as `None` for Books, as explicitly permitted by the assignment specifications. An optional `--scrape-details` flag is provided if detail crawling is desired.
2. **Deterministic Deduplication**:
   - Quotes use the first 50 characters of quote text + author because minor typographical differences often appear at the end of long quotes.
3. **Server-Rendered HTML**:
   - Both target websites use static server-rendered HTML. No client-side JavaScript execution (via Selenium/Playwright) is required or used.

---

## Interview Q&A Guide

### Q1: Why use `requests.Session` instead of standalone `requests.get()`?
> **Answer**: `requests.Session` reuses underlying TCP connections via HTTP keep-alive, reducing SSL/TLS handshake overhead, lowering latency across 60+ consecutive requests, and allowing session-wide configuration of default headers, cookies, and retry adapters.

### Q2: How did you implement dynamic pagination safely?
> **Answer**: We inspect the DOM on each page for `li.next > a`. If found, `urllib.parse.urljoin` resolves the relative URL (e.g., `catalogue/page-2.html` on the root page, or `page-3.html` on subsequent pages) against the current page URL. When the selector returns `None`, pagination terminates cleanly without hardcoding page numbers.

### Q3: Why SHA-256 hashing for duplicate detection?
> **Answer**: SHA-256 provides a deterministic fingerprint of the normalized identifying fields. We can store these fingerprints in a Python set and efficiently detect duplicate records while keeping the duplicate-detection logic simple and consistent.

### Q4: How is fault tolerance achieved?
> **Answer**: At the network level, `urllib3.util.retry.Retry` handles transient 5xx and 429 status codes. At the source level, Books and Quotes extraction run in isolated `try...except` blocks so one source failing does not halt the other. At the record level, card parsing errors are logged without interrupting the rest of the page.

---

## AI Usage Summary

Full details regarding AI assistance, prompting strategies, manual reviews, and code verification are documented in [`AI_USAGE.md`](AI_USAGE.md).
