"""The public book use cases with an in-memory catalog (no database)."""

from datetime import UTC, date, datetime

import pytest

from src.app.catalog.entities import (
    BookDetail,
    DailyLow,
    ProductCondition,
    PublicOffer,
)
from src.app.catalog.isbn import InvalidIsbnError
from src.app.catalog.ports import BookCatalogReader
from src.app.catalog.use_cases import (
    BookNotFoundError,
    GetBookUseCase,
    GetDailyLowsUseCase,
    SearchBooksUseCase,
)

ISBN13 = "9788535914849"
ISBN10 = "8535914846"
NOW = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)


def offer(condition, price, available=True, store="estante_virtual"):
    return PublicOffer(
        store=store,
        url=f"https://{store}/{condition}/{price}",
        condition=condition,
        price=price,
        is_available=available,
        last_checked_at=NOW,
    )


BOOK = BookDetail(
    isbn13=ISBN13,
    title="1984",
    attributes={"authors": ["George Orwell"], "cover_url": "https://c/1984.jpg"},
    offers=(
        offer(ProductCondition.USED, 17.5),
        offer(ProductCondition.USED, 9.0, available=False),
        offer(ProductCondition.NEW, 54.9, store="martins_fontes"),
        offer(ProductCondition.NEW, 49.9, store="livraria_da_vila"),
    ),
)


class InMemoryCatalog(BookCatalogReader):
    def __init__(self, books=(BOOK,)):
        self.books = {b.isbn13: b for b in books}
        self.searches, self.lows_since = [], []

    def search(self, term, limit, offset):
        self.searches.append((term, limit, offset))
        found = [b.summary() for b in self.books.values() if term in b.title]
        return found[offset : offset + limit], len(found)

    def get_book(self, isbn13):
        return self.books.get(isbn13)

    def daily_lows(self, isbn13, since):
        self.lows_since.append(since)
        return [DailyLow(day=date(2026, 11, 9), condition="used", price=17.5)]


class TestBookDetail:
    def test_lowest_counts_only_offers_in_stock(self):
        assert BOOK.lowest(ProductCondition.USED) == 17.5  # not the 9.00 sold out
        assert BOOK.lowest(ProductCondition.NEW) == 49.9

    def test_lowest_is_none_without_offers_in_that_condition(self):
        book = BookDetail(isbn13=ISBN13, title="x", offers=(offer("used", 10),))

        assert book.lowest(ProductCondition.NEW) is None

    def test_summary_carries_authors_cover_and_lows(self):
        summary = BOOK.summary()

        assert summary.authors == ("George Orwell",)
        assert summary.cover_url == "https://c/1984.jpg"
        assert (summary.lowest_new, summary.lowest_used) == (49.9, 17.5)
        assert summary.offer_count == 4


class TestSearchBooks:
    def test_searches_titles_and_authors(self):
        catalog = InMemoryCatalog()

        result = SearchBooksUseCase(catalog).execute("  198  ")

        assert [b.isbn13 for b in result.books] == [ISBN13]
        assert catalog.searches == [("198", 20, 0)]

    def test_an_isbn_is_an_exact_lookup(self):
        catalog = InMemoryCatalog()

        result = SearchBooksUseCase(catalog).execute("85-359-1484-6")  # ISBN-10

        assert [b.isbn13 for b in result.books] == [ISBN13]
        assert result.total == 1
        assert catalog.searches == []

    def test_an_unknown_isbn_finds_nothing(self):
        result = SearchBooksUseCase(InMemoryCatalog()).execute("9780306406157")

        assert (result.books, result.total) == ([], 0)

    def test_a_one_letter_term_finds_nothing(self):
        catalog = InMemoryCatalog()

        assert SearchBooksUseCase(catalog).execute("a").total == 0
        assert catalog.searches == []

    def test_page_size_is_capped(self):
        catalog = InMemoryCatalog()

        SearchBooksUseCase(catalog).execute("1984", limit=500, offset=-3)

        assert catalog.searches == [("1984", 50, 0)]


class TestGetBook:
    def test_accepts_isbn_10_and_13(self):
        use_case = GetBookUseCase(InMemoryCatalog())

        assert use_case.execute(ISBN10) is BOOK
        assert use_case.execute("978-85-359-1484-9") is BOOK

    def test_an_invalid_isbn_is_refused(self):
        with pytest.raises(InvalidIsbnError):
            GetBookUseCase(InMemoryCatalog()).execute("123")

    def test_an_unknown_book_is_not_found(self):
        with pytest.raises(BookNotFoundError):
            GetBookUseCase(InMemoryCatalog()).execute("9780306406157")


class TestDailyLows:
    def test_asks_for_the_last_days(self):
        catalog = InMemoryCatalog()

        lows = GetDailyLowsUseCase(catalog, now=lambda: NOW).execute(ISBN13, 30)

        assert lows[0].price == 17.5
        assert catalog.lows_since == [datetime(2026, 10, 11, 15, 0, tzinfo=UTC)]

    def test_the_window_is_capped_at_a_year(self):
        catalog = InMemoryCatalog()

        GetDailyLowsUseCase(catalog, now=lambda: NOW).execute(ISBN13, 9999)

        assert catalog.lows_since == [datetime(2025, 11, 10, 15, 0, tzinfo=UTC)]

    def test_an_unknown_book_is_not_found(self):
        with pytest.raises(BookNotFoundError):
            GetDailyLowsUseCase(InMemoryCatalog()).execute("9780306406157")
