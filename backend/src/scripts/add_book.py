"""Find or create a book in the catalog from its ISBN.

Composition root for the catalog's book lookup: it wires the BrasilAPI adapter
and the database repository into the use case.

Usage (from backend/):
    python -m src.scripts.add_book 978-85-359-1484-9
"""

import argparse
import sys

from src.app.catalog.adapters.brasilapi_books import BrasilApiBookMetadata
from src.app.catalog.isbn import InvalidIsbnError
from src.app.catalog.persistence.repositories import CanonicalProductRepository
from src.app.catalog.ports import BookMetadataUnavailableError
from src.app.catalog.use_cases import BookNotFoundError, GetOrCreateBookByIsbnUseCase
from src.app.infrastructure.database_config import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("isbn", help="ISBN-10 or ISBN-13, with or without hyphens")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        use_case = GetOrCreateBookByIsbnUseCase(
            CanonicalProductRepository(db), BrasilApiBookMetadata()
        )
        book = use_case.execute(args.isbn)
    except InvalidIsbnError as exc:
        print(f"Invalid ISBN: {exc}")
        return 2
    except BookNotFoundError:
        print("No metadata source knows this book.")
        return 1
    except BookMetadataUnavailableError as exc:
        print(f"Metadata source unavailable: {exc}")
        return 3
    finally:
        db.close()

    authors = ", ".join(book.attributes.get("authors", []))
    print(f"#{book.id} {book.title} ({authors})")
    for identifier in book.identifiers:
        print(f"  {identifier.kind.value}: {identifier.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
