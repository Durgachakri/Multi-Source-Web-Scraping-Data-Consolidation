"""Main ETL Pipeline Orchestrator.

Orchestrates the entire multi-source extraction, cleaning, validation,
deduplication, consolidation, and output generation pipeline:
    Scrape -> Clean -> Validate -> Deduplicate -> Consolidate -> Save

Adheres to:
- Independent exception handling per source (Books and Quotes)
- Structured logging to both logs/scraper.log and stdout
- Generation of output/final_dataset.csv and output/summary_report.json
- Fully reconciled summary metrics matching CSV row counts
"""

import argparse
import csv
from datetime import datetime, timezone
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Tuple

# Ensure local package imports work seamlessly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from processing.cleaning import clean_record
from processing.deduplication import deduplicate_records
from processing.validation import validate_record
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper

# Fixed common dataset schema
DATASET_COLUMNS: List[str] = [
    "source",
    "source_url",
    "name_or_title",
    "category",
    "price",
    "rating",
    "author",
    "tags",
    "description",
    "scraped_at",
]


def setup_logging(logs_dir: str) -> logging.Logger:
    """Configure structured logging to both file and console.

    Args:
        logs_dir: Path to directory where scraper.log will be written.

    Returns:
        Configured root logger for the application.
    """
    os.makedirs(logs_dir, exist_ok=True)
    log_file_path = os.path.join(logs_dir, "scraper.log")

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Root logger configuration
    app_logger = logging.getLogger()
    app_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if re-initialized
    if not app_logger.handlers:
        # File handler (UTF-8 encoded)
        file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        app_logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        app_logger.addHandler(console_handler)

    return app_logger


def run_books_scraper(
    delay: float = 0.5,
    max_pages: int | None = None,
    scrape_details: bool = False,
) -> List[Dict[str, Any]]:
    """Execute Books to Scrape scraper with isolated error handling.

    Returns:
        List of raw extracted book records.
    """
    logger = logging.getLogger("pipeline.books")
    logger.info("Initializing Books to Scrape extraction stage...")

    try:
        with BooksScraper(
            request_delay=delay,
            max_pages=max_pages,
            scrape_details=scrape_details,
        ) as scraper:
            records = scraper.scrape_all()
            logger.info("Books extraction finished successfully with %d records.", len(records))
            return records
    except Exception as exc:
        logger.error(
            "Fatal failure during Books to Scrape stage: %s",
            exc,
            exc_info=True,
        )
        return []


def run_quotes_scraper(
    delay: float = 0.5,
    max_pages: int | None = None,
) -> List[Dict[str, Any]]:
    """Execute Quotes to Scrape scraper with isolated error handling.

    Returns:
        List of raw extracted quote records.
    """
    logger = logging.getLogger("pipeline.quotes")
    logger.info("Initializing Quotes to Scrape extraction stage...")

    try:
        with QuotesScraper(
            request_delay=delay,
            max_pages=max_pages,
        ) as scraper:
            records = scraper.scrape_all()
            logger.info("Quotes extraction finished successfully with %d records.", len(records))
            return records
    except Exception as exc:
        logger.error(
            "Fatal failure during Quotes to Scrape stage: %s",
            exc,
            exc_info=True,
        )
        return []


def save_csv(records: List[Dict[str, Any]], filepath: str) -> None:
    """Save consolidated records to CSV file using csv.DictWriter with UTF-8 encoding.

    Args:
        records: Final consolidated records list.
        filepath: Destination path for final_dataset.csv.
    """
    logger = logging.getLogger("pipeline.save_csv")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=DATASET_COLUMNS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()

        for record in records:
            # Map None values to empty strings for clean CSV representation
            row = {col: (record.get(col) if record.get(col) is not None else "") for col in DATASET_COLUMNS}
            writer.writerow(row)

    logger.info("Saved %d records to CSV: %s", len(records), filepath)


def save_summary_report(report_data: Dict[str, Any], filepath: str) -> None:
    """Save execution metrics to summary_report.json.

    Args:
        report_data: Dictionary containing reconciled run metrics.
        filepath: Destination path for summary_report.json.
    """
    logger = logging.getLogger("pipeline.save_summary")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, mode="w", encoding="utf-8") as jsonfile:
        json.dump(report_data, jsonfile, indent=2, ensure_ascii=False)

    logger.info("Saved summary report to JSON: %s", filepath)


def run_pipeline(
    max_pages: int | None = None,
    delay: float = 0.5,
    source_filter: str = "all",
    scrape_details: bool = False,
    output_dir: str | None = None,
    logs_dir: str | None = None,
) -> Dict[str, Any]:
    """Execute the full end-to-end web scraping ETL pipeline.

    Stages:
        1. Scrape raw data from target websites.
        2. Clean and standardize all records to common schema.
        3. Validate schema compliance and record rejection reasons.
        4. Deduplicate records using deterministic SHA-256 fingerprints.
        5. Consolidate and export to CSV and JSON summary.

    Returns:
        Summary metrics dictionary.
    """
    base_dir = CURRENT_DIR
    out_dir = output_dir or os.path.join(base_dir, "output")
    log_dir = logs_dir or os.path.join(base_dir, "logs")

    logger = setup_logging(log_dir)

    start_datetime = datetime.now(timezone.utc)
    start_time_iso = start_datetime.isoformat()
    start_perf = time.perf_counter()

    logger.info("==============================================================")
    logger.info("Starting Multi-Source Web Scraping ETL Pipeline")
    logger.info("Configuration: source=%s, delay=%.2fs, max_pages=%s", source_filter, delay, max_pages)
    logger.info("==============================================================")

    # 1. SCRAPING STAGE (Independent fault tolerance)
    raw_books: List[Dict[str, Any]] = []
    raw_quotes: List[Dict[str, Any]] = []

    if source_filter in ("all", "books"):
        raw_books = run_books_scraper(
            delay=delay,
            max_pages=max_pages,
            scrape_details=scrape_details,
        )

    if source_filter in ("all", "quotes"):
        raw_quotes = run_quotes_scraper(
            delay=delay,
            max_pages=max_pages,
        )

    # 2. CLEANING STAGE
    logger.info("Pipeline Stage: Cleaning and schema standardization...")
    cleaned_books = [clean_record(r) for r in raw_books]
    cleaned_quotes = [clean_record(r) for r in raw_quotes]

    # 3. VALIDATION STAGE
    logger.info("Pipeline Stage: Validating records against schema and business rules...")
    rejection_reasons: Dict[str, int] = {}
    valid_records: List[Dict[str, Any]] = []

    def validate_source_records(
        records: List[Dict[str, Any]], source_name: str
    ) -> Tuple[List[Dict[str, Any]], int]:
        valid_items: List[Dict[str, Any]] = []
        rejected_count = 0

        for r in records:
            errors = validate_record(r)
            if errors:
                rejected_count += 1
                for err in errors:
                    rejection_reasons[err] = rejection_reasons.get(err, 0) + 1
                logger.warning(
                    "Rejected record from '%s' ('%s'): %s",
                    source_name,
                    r.get("name_or_title", "Unknown"),
                    ", ".join(errors),
                )
            else:
                valid_items.append(r)

        return valid_items, rejected_count

    valid_books, rejected_books_count = validate_source_records(cleaned_books, "Books to Scrape")
    valid_quotes, rejected_quotes_count = validate_source_records(cleaned_quotes, "Quotes to Scrape")

    valid_records.extend(valid_books)
    valid_records.extend(valid_quotes)

    # 4. DEDUPLICATION STAGE
    logger.info("Pipeline Stage: Deterministic fingerprint deduplication...")
    unique_records, duplicate_records = deduplicate_records(valid_records)
    duplicates_found = len(duplicate_records)

    if duplicates_found > 0:
        logger.warning(
            "Identified and excluded %d duplicate records from final dataset.",
            duplicates_found,
        )
    else:
        logger.info("Duplicate check complete: 0 duplicate records detected.")

    # 5. CONSOLIDATION AND OUTPUT GENERATION
    logger.info("Pipeline Stage: Generating output artifacts...")
    csv_file_path = os.path.join(out_dir, "final_dataset.csv")
    json_file_path = os.path.join(out_dir, "summary_report.json")

    save_csv(unique_records, csv_file_path)

    end_datetime = datetime.now(timezone.utc)
    end_time_iso = end_datetime.isoformat()
    duration_seconds = round(time.perf_counter() - start_perf, 2)

    # Build and reconcile summary metrics
    summary_report: Dict[str, Any] = {
        "run": {
            "start_time": start_time_iso,
            "end_time": end_time_iso,
            "duration_seconds": duration_seconds,
        },
        "sources": {
            "Books to Scrape": {
                "raw_records": len(raw_books),
                "cleaned_records": len(cleaned_books),
                "rejected_records": rejected_books_count,
            },
            "Quotes to Scrape": {
                "raw_records": len(raw_quotes),
                "cleaned_records": len(cleaned_quotes),
                "rejected_records": rejected_quotes_count,
            },
        },
        "rejection_reasons": rejection_reasons,
        "duplicates_found": duplicates_found,
        "final_record_count": len(unique_records),
    }

    save_summary_report(summary_report, json_file_path)

    logger.info("==============================================================")
    logger.info("ETL Pipeline Execution Finished Successfully!")
    logger.info("Total Duration: %.2f seconds", duration_seconds)
    logger.info(
        "Sources Extracted: Books=%d, Quotes=%d",
        len(raw_books),
        len(raw_quotes),
    )
    logger.info(
        "Validation: Valid=%d, Rejected=%d",
        len(valid_records),
        rejected_books_count + rejected_quotes_count,
    )
    logger.info("Deduplication: Duplicates Found=%d", duplicates_found)
    logger.info("Final Cleaned Dataset: %d records in %s", len(unique_records), csv_file_path)
    logger.info("==============================================================")

    return summary_report


def parse_cli_args() -> argparse.Namespace:
    """Parse command line arguments for flexible pipeline execution."""
    parser = argparse.ArgumentParser(
        description="Multi-source Web Scraping ETL Pipeline (Books & Quotes to Scrape)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=["all", "books", "quotes"],
        default="all",
        help="Target data source(s) to scrape",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between successive HTTP requests",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to scrape per source (default: scrape all dynamically)",
    )
    parser.add_argument(
        "--scrape-details",
        action="store_true",
        default=False,
        help="Fetch individual detail pages for books category and description",
    )
    return parser.parse_args()


def main() -> None:
    """CLI Entrypoint."""
    args = parse_cli_args()
    run_pipeline(
        max_pages=args.max_pages,
        delay=args.delay,
        source_filter=args.source,
        scrape_details=args.scrape_details,
    )


if __name__ == "__main__":
    main()
