# AI Usage Disclosure & Transparency Report

This document outlines the usage of Artificial Intelligence tools during the design, implementation, debugging, and verification of the web-scraping assignment, in strict compliance with the project guidelines.

---

## 1. AI Tool Used
- **Tool**: Google Gemini, Antigravity IDE
- **Role**: Technical architecture pair-programmer, test suite generator, and code reviewer.

---

## 2. Areas Where AI Was Utilized

AI assistance was utilized across the following stages:
1. **Architectural Design**:
   - Outlining the multi-stage ETL lifecycle: $\text{Scrape} \rightarrow \text{Clean} \rightarrow \text{Validate} \rightarrow \text{Deduplicate} \rightarrow \text{Consolidate} \rightarrow \text{Save}$.
   - Modularizing code across `scrapers/`, `processing/`, and `tests/` to maintain clean separation of concerns.
2. **Initial Boilerplate & Scaffold Generation**:
   - Creating the skeleton structure for `BaseScraper` configuring `requests.Session` with `HTTPAdapter` and `urllib3.util.retry.Retry`.
   - Initial draft of CSS selectors for `BooksScraper` and `QuotesScraper`.
3. **Regex & String Sanitation Helpers**:
   - Crafting regex rules for `clean_price` and typographic quote removal in `strip_quotes`.
4. **Unit Test Suite Generation**:
   - Drafting parameterized test fixtures for `test_cleaning.py`, `test_validation.py`, and `test_deduplication.py`.
5. **Documentation & Interview Guide**:
   - Structuring sections for `README.md` and articulating technical interview questions and answers.

---

## 3. Representative Prompts Provided to AI

### Prompt 1 (Base HTTP Layer):
> *"Design a reusable BaseScraper class in Python using requests.Session, urllib3 Retry with exponential backoff on 429, 500, 502, 503, 504, a configurable polite request delay of 0.5s, explicit UTF-8 response encoding, and parsing with BeautifulSoup(..., 'lxml')."*

### Prompt 2 (Dynamic Pagination):
> *"Write a Books to Scrape scraper that dynamically follows li.next > a until no next page exists. Ensure it extracts the full title from the title attribute, price, star rating class, and resolves relative URLs using urllib.parse.urljoin. Do not hardcode page ranges."*

### Prompt 3 (Deterministic Deduplication):
> *"Implement a deduplication module in Python that generates a SHA-256 fingerprint from normalized fields (lowercased, punctuation stripped, whitespace collapsed). For books: source + title. For quotes: source + author + first 50 chars of title. Ensure 'Example Book Title', 'Example Book Title ', and 'EXAMPLE BOOK TITLE' produce identical fingerprints."*

### Prompt 4 (Unit Testing):
> *"Generate comprehensive pytest test cases for data cleaning, validation, and deduplication that execute 100% offline without requiring internet access."*

---

## 4. Manual Reviews & Code Refinements

AI-generated code was not accepted blindly. The following critical reviews and corrections were made:

### 1. Relative URL Resolution on Books to Scrape
- **Initial AI Suggestion**: Concatenated `https://books.toscrape.com/catalogue/` with `next_href`.
- **Bug/Issue Identified**: On page 1 (`https://books.toscrape.com/index.html`), the next link is `catalogue/page-2.html`. However, on page 2 (`https://books.toscrape.com/catalogue/page-2.html`), the next link is `page-3.html`. Hardcoded string concatenation resulted in broken URLs like `.../catalogue/catalogue/page-2.html`.
- **Manual Fix**: Replaced naive string concatenation with standard `urllib.parse.urljoin(current_url, next_href)`, which resolves relative path references correctly according to RFC 3986.

### 2. Typographical Quotation Marks in Quotes
- **Initial AI Suggestion**: Used standard Python `.strip('"\'')`.
- **Bug/Issue Identified**: Quotes on Quotes to Scrape are rendered using Unicode curly quotes (`\u201c` `“` and `\u201d` `”`). Standard ASCII strip left the curly quotation marks attached to the quote text.
- **Manual Fix**: Expanded `strip_quotes()` to encompass unicode curly and typographic quotation marks (`"`, `'`, `“`, `”`, `‘`, `’`, `«`, `»`, `„`, `‟`).

### 3. Detail Page Crawling vs. Throughput Constraint
- **Initial AI Suggestion**: Automatically sent GET requests to each book's individual detail page to extract category and description.
- **Performance Issue**: 1,000 books $\times$ 0.5s polite delay would increase the pipeline execution time to 500+ seconds (~8.5 minutes).
- **Manual Architecture Decision**: Made detail page crawling an optional opt-in CLI flag (`--scrape-details`), keeping catalog scraping fast (~30 seconds for all 1,000 books) while setting category and description to `None` by default and documenting this transparently in the README as permitted by the assignment specifications.

### 4. Pytest PYTHONPATH Discovery
- **Initial AI Suggestion**: Relied on implicit local directory discovery.
- **Bug/Issue Identified**: Running `pytest` from parent directories threw `ModuleNotFoundError: No module named 'processing'`.
- **Manual Fix**: Added `tests/conftest.py` ensuring the assignment root directory is dynamically added to `sys.path`.

---

## 5. Verification & Testing

Every component was verified and tested in the runtime environment:
- [x] Ran `python -m pytest scraping_assignment/tests/` $\rightarrow$ 54 passing offline unit tests.
- [x] Verified dynamic pagination across all 50 catalog pages of Books to Scrape.
- [x] Verified dynamic pagination across all 10 pages of Quotes to Scrape.
- [x] Executed `python main.py` end-to-end.
- [x] Verified generated `output/final_dataset.csv` contains valid header and clean data.
- [x] Verified `output/summary_report.json` metrics reconcile with CSV row counts.
- [x] Inspected `logs/scraper.log` to confirm informative logs, timestamps, and error handling.
