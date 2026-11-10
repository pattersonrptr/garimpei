"""Collect offers for some ISBNs and send them to the backend.

Composition root: wires the polite HTTP client, the store adapters and the API
sink. Credentials come from the same variables the scraper worker uses. Each
store gets its own HTTP client (its own pauses and robots.txt) and runs after
the previous one, so only one request is ever in flight.

Usage (from scrapers/):
    python -m src.collectors.run 9788535914849 9788532530271
    python -m src.collectors.run --store martins-fontes 9788535914849
    python -m src.collectors.run --file ../backend/seeds/books_bestsellers.csv
"""

import argparse
import csv
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

from src.collectors.api_sink import ApiOfferSink, login
from src.collectors.polite_http import PoliteHttpClient
from src.collectors.ports import OfferSource
from src.collectors.stores.estante_virtual import EstanteVirtualSource
from src.collectors.stores.vtex import VtexSource
from src.collectors.use_cases import CollectOffers

STORES: dict[str, Callable[[], OfferSource]] = {
    "estante-virtual": lambda: EstanteVirtualSource(PoliteHttpClient()),
    "livraria-da-vila": lambda: VtexSource(
        PoliteHttpClient(),
        store_name="livraria_da_vila",
        base_url="https://www.livrariadavila.com.br",
    ),
    "martins-fontes": lambda: VtexSource(
        PoliteHttpClient(),
        store_name="martins_fontes",
        base_url="https://www.martinsfontespaulista.com.br",
    ),
}


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

    base_url = os.getenv("API_URL", "http://localhost:8000")
    token = login(
        base_url,
        os.environ["CELERY_WORKER_USERNAME"],
        os.environ["CELERY_WORKER_PASSWORD"],
    )
    sink = ApiOfferSink(base_url, token)
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
