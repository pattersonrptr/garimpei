"""Load the seed list of books into the catalog (one command, safe to rerun).

Reads ISBNs from a CSV with an ``isbn13`` column (default: the all-time
best-sellers list) and creates each book from its metadata if it is not in the
catalog yet. Composition root: wires BrasilAPI and the database repository.

Usage (from backend/):
    python -m src.scripts.load_seed_books
    python -m src.scripts.load_seed_books --file seeds/other.csv --pause 2
"""

import argparse
import csv
import sys
import time
from pathlib import Path

from src.app.catalog.adapters.brasilapi_books import BrasilApiBookMetadata
from src.app.catalog.persistence.repositories import CanonicalProductRepository
from src.app.catalog.use_cases import (
    GetOrCreateBookByIsbnUseCase,
    LoadSeedBooksUseCase,
)
from src.app.infrastructure.database_config import SessionLocal

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "seeds" / "books_bestsellers.csv"


def read_seed_isbns(path: Path) -> list[str]:
    """The non-empty values of the ``isbn13`` column, in file order."""
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "isbn13" not in reader.fieldnames:
            raise ValueError(f"{path} has no isbn13 column")
        return [row["isbn13"].strip() for row in reader if row["isbn13"].strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument(
        "--pause", type=float, default=1.0, help="seconds between metadata lookups"
    )
    args = parser.parse_args()

    isbns = read_seed_isbns(args.file)
    db = SessionLocal()
    try:
        products = CanonicalProductRepository(db)
        use_case = LoadSeedBooksUseCase(
            GetOrCreateBookByIsbnUseCase(products, BrasilApiBookMetadata()),
            products,
            pause=lambda: time.sleep(args.pause),
        )
        report = use_case.execute(isbns)
    finally:
        db.close()

    print(
        f"{len(isbns)} ISBNs: {len(report.created)} created, "
        f"{len(report.existing)} already in the catalog, {len(report.failed)} failed"
    )
    for isbn, reason in report.failed:
        print(f"  failed {isbn}: {reason}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
