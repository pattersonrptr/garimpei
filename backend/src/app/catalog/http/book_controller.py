"""Public book pages API: search, a book with its offers, daily lows.

No login: this is what the public comparator pages read (Phase 3). Read-only,
no personal data, page size capped. This module is the composition root for
the catalog's read model.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.app.catalog.entities import (
    BookDetail,
    BookSummary,
    DailyLow,
    PriceVerdict,
    PublicOffer,
)
from src.app.catalog.isbn import InvalidIsbnError
from src.app.catalog.persistence.repositories import BookCatalogRepository
from src.app.catalog.ports import BookCatalogReader
from src.app.catalog.use_cases import (
    MAX_HISTORY_DAYS,
    MAX_PAGE_SIZE,
    BookNotFoundError,
    GetBookUseCase,
    GetDailyLowsUseCase,
    JudgeBookPricesUseCase,
    ListBooksUseCase,
    SearchBooksUseCase,
)
from src.app.infrastructure.database_config import get_db
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse

router = APIRouter(tags=["books (public)"], prefix="/books")

JSONAPI = "application/vnd.api+json"


def get_book_catalog(db=Depends(get_db)) -> BookCatalogReader:
    return BookCatalogRepository(db)


def _iso(moment) -> str | None:
    return moment.isoformat() if moment else None


def _summary(book: BookSummary) -> dict:
    return {
        "type": "books",
        "id": book.isbn13,
        "attributes": {
            "isbn13": book.isbn13,
            "title": book.title,
            "authors": list(book.authors),
            "cover_url": book.cover_url,
            "lowest_new": book.lowest_new,
            "lowest_used": book.lowest_used,
            "offer_count": book.offer_count,
        },
    }


def _offer(offer: PublicOffer) -> dict:
    return {
        "store": offer.store,
        "url": offer.url,
        "condition": offer.condition.value,
        "price": offer.price,
        "is_available": offer.is_available,
        "last_checked_at": _iso(offer.last_checked_at),
    }


def _verdict(verdict: PriceVerdict) -> dict:
    return {
        "condition": verdict.condition.value,
        "status": verdict.status.value,
        "current": verdict.current,
        "days": verdict.days,
        "low": verdict.low,
        "high": verdict.high,
        "p25": verdict.p25,
        "p75": verdict.p75,
    }


def _detail(book: BookDetail, verdicts: list[PriceVerdict]) -> dict:
    summary = book.summary()
    attributes = {
        key: book.attributes.get(key)
        for key in ("subtitle", "publisher", "year", "page_count", "synopsis")
    }
    resource = _summary(summary)
    resource["attributes"].update(attributes)
    resource["attributes"]["offers"] = [_offer(o) for o in book.offers]
    resource["attributes"]["verdicts"] = [_verdict(v) for v in verdicts]
    return resource


def _daily_low(low: DailyLow) -> dict:
    return {
        "day": low.day.isoformat(),
        "condition": low.condition.value,
        "price": low.price,
    }


def _not_found(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=JsonApiErrorResponse(
            errors=[
                JsonApiError(
                    status="404",
                    code="BOOK_NOT_FOUND",
                    title="Book not found",
                    detail=detail,
                    source={"parameter": "isbn"},
                )
            ]
        ).model_dump(),
        media_type=JSONAPI,
    )


@router.get("/")
def search_books(
    q: str = Query("", description="Title, author or ISBN"),
    limit: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    books: BookCatalogReader = Depends(get_book_catalog),
):
    """Books matching a title, an author or an ISBN, books in stock first."""
    result = SearchBooksUseCase(books).execute(q, limit, offset)
    return JSONResponse(
        content={
            "data": [_summary(b) for b in result.books],
            "meta": {"total": result.total},
        },
        media_type=JSONAPI,
    )


@router.get("/index")
def list_books(
    limit: int = Query(MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    books: BookCatalogReader = Depends(get_book_catalog),
):
    """Every book in the catalog, a page at a time (the public sitemap)."""
    result = ListBooksUseCase(books).execute(limit, offset)
    return JSONResponse(
        content={
            "data": [_summary(b) for b in result.books],
            "meta": {"total": result.total},
        },
        media_type=JSONAPI,
    )


@router.get("/{isbn}")
def get_book(isbn: str, books: BookCatalogReader = Depends(get_book_catalog)):
    """A book with every store's offer, in stock and cheapest first, and the
    price verdict for new and used copies.

    Returns 404 for an unknown book or an invalid ISBN.
    """
    try:
        book = GetBookUseCase(books).execute(isbn)
    except (InvalidIsbnError, BookNotFoundError):
        return _not_found(f"No book with ISBN {isbn}")
    verdicts = JudgeBookPricesUseCase(books).execute(book)
    return JSONResponse(content={"data": _detail(book, verdicts)}, media_type=JSONAPI)


@router.get("/{isbn}/price-history")
def get_price_history(
    isbn: str,
    days: int = Query(90, ge=1, le=MAX_HISTORY_DAYS),
    books: BookCatalogReader = Depends(get_book_catalog),
):
    """The book's lowest price per day and condition (Brazil's days)."""
    try:
        lows = GetDailyLowsUseCase(books).execute(isbn, days)
    except (InvalidIsbnError, BookNotFoundError):
        return _not_found(f"No book with ISBN {isbn}")
    return JSONResponse(
        content={"data": [_daily_low(low) for low in lows], "meta": {"days": days}},
        media_type=JSONAPI,
    )
