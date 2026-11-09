"""Collect offers for some ISBNs from one store and send them to the backend.

Composition root: wires the polite HTTP client, the store adapter and the API
sink. Credentials come from the same variables the scraper worker uses.

Usage (from scrapers/):
    python -m src.collectors.run 9788535914849 9788532530271
    python -m src.collectors.run --file ../backend/seeds/books_bestsellers.csv
"""

import argparse
import csv
import logging
import os
import sys
from pathlib import Path

from src.collectors.api_sink import ApiOfferSink, login
from src.collectors.polite_http import PoliteHttpClient
from src.collectors.stores.estante_virtual import EstanteVirtualSource
from src.collectors.use_cases import CollectOffers


def read_isbns(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        return [
            row["isbn13"].strip() for row in csv.DictReader(f) if row["isbn13"].strip()
        ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("isbns", nargs="*")
    parser.add_argument("--file", type=Path, help="CSV with an isbn13 column")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    isbns = args.isbns + (read_isbns(args.file) if args.file else [])
    if not isbns:
        parser.error("give ISBNs or --file")

    base_url = os.getenv("API_URL", "http://localhost:8000")
    token = login(
        base_url,
        os.environ["CELERY_WORKER_USERNAME"],
        os.environ["CELERY_WORKER_PASSWORD"],
    )
    source = EstanteVirtualSource(PoliteHttpClient())
    report = CollectOffers(source, ApiOfferSink(base_url, token)).execute(isbns)

    print(
        f"{source.store_name}: {len(isbns)} ISBNs, {report.sent} offers sent, "
        f"{len(report.not_found)} not found, {len(report.failed)} failed"
    )
    for isbn, reason in report.failed:
        print(f"  failed {isbn}: {reason}")
    if report.blocked:
        print(f"  stopped: {report.blocked} ({len(report.skipped)} ISBNs skipped)")
    return 1 if report.failed or report.blocked else 0


if __name__ == "__main__":
    sys.exit(main())
