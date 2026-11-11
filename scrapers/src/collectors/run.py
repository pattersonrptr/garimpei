"""Collect offers for some ISBNs and send them to the backend.

For a manual run; the daily schedule is the collect_daily_offers Celery task.
The wiring lives in src/collectors/wiring.py. The stores run one after the
other, so only one request is ever in flight.

Usage (from scrapers/):
    python -m src.collectors.run 9788535914849 9788532530271
    python -m src.collectors.run --store martins-fontes 9788535914849
    python -m src.collectors.run --file ../backend/seeds/books_bestsellers.csv
"""

import argparse
import csv
import logging
import sys
from pathlib import Path

from src.collectors.use_cases import CollectOffers
from src.collectors.wiring import STORES, offer_sink


def read_isbns(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        return [
            row["isbn13"].strip() for row in csv.DictReader(f) if row["isbn13"].strip()
        ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("isbns", nargs="*")
    parser.add_argument("--file", type=Path, help="CSV with an isbn13 column")
    parser.add_argument(
        "--store",
        choices=[*STORES, "all"],
        default="all",
        help="one store, or all of them in turn (default)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    isbns = args.isbns + (read_isbns(args.file) if args.file else [])
    if not isbns:
        parser.error("give ISBNs or --file")

    sink = offer_sink()
    names = list(STORES) if args.store == "all" else [args.store]

    problems = False
    for name in names:
        source = STORES[name]()
        report = CollectOffers(source, sink).execute(isbns)
        print(
            f"{source.store_name}: {len(isbns)} ISBNs, {report.sent} offers sent, "
            f"{len(report.not_found)} not found, {len(report.failed)} failed"
        )
        for isbn, reason in report.failed:
            print(f"  failed {isbn}: {reason}")
        if report.blocked:
            print(f"  stopped: {report.blocked} ({len(report.skipped)} ISBNs skipped)")
        problems = problems or bool(report.failed or report.blocked)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
