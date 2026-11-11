"""BookCatalogRepository (the public pages' read model) on SQLite in memory."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.catalog.entities import (
    CanonicalProduct,
    IdentifierKind,
    ProductCategory,
    ProductCondition,
    ProductIdentifier,
)
from src.app.catalog.persistence.models import PriceHistory as PriceHistoryModel
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.catalog.persistence.repositories import (
    BookCatalogRepository,
    CanonicalProductRepository,
)
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.database_config import Base

EV, VILA = 1, 2


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all(
        [
            SourceWebsiteModel(id=EV, name="estante_virtual", base_url="https://ev"),
            SourceWebsiteModel(id=VILA, name="livraria_da_vila", base_url="https://v"),
        ]
    )
    session.commit()
    yield session
    session.close()


def a_book(db, isbn, title, authors):
    return CanonicalProductRepository(db).create(
        CanonicalProduct(
            category=ProductCategory.BOOK,
            title=title,
            attributes={"authors": authors, "synopsis": "um piloto no deserto"},
            identifiers=[ProductIdentifier(kind=IdentifierKind.ISBN13, value=isbn)],
        )
    )


def an_offer(db, book, store, condition, points, available=True, url=None):
    """An offer with price points given as (naive UTC datetime, price)."""
    offer = ProductModel(
        url=url or f"https://{store}/{book.id}/{condition}",
        title=book.title,
        source_website_id=store,
        condition=condition,
        is_available=available,
        canonical_product_id=book.id,
    )
    db.add(offer)
    db.flush()
    db.add_all(
        PriceHistoryModel(product_id=offer.id, price=price, created_at=moment)
        for moment, price in points
    )
    db.commit()
    return offer


@pytest.fixture
def catalog(db):
    orwell = a_book(db, "9788535914849", "1984", ["George Orwell"])
    marquez = a_book(
        db, "9788501012074", "Cem anos de solidão", ["Gabriel García Márquez"]
    )
    a_book(db, "9788535902778", "A revolução dos bichos", ["George Orwell"])
    an_offer(db, orwell, EV, "used", [(datetime(2026, 11, 9, 12), 20.0)])
    an_offer(db, orwell, EV, "new", [(datetime(2026, 11, 10, 1), 55.0)])
    an_offer(
        db,
        orwell,
        VILA,
        "new",
        [(datetime(2026, 11, 8, 12), 60.0), (datetime(2026, 11, 10, 2), 49.9)],
    )
    an_offer(db, marquez, EV, "used", [(datetime(2026, 11, 9, 12), 30.0)])
    an_offer(
        db, marquez, VILA, "new", [(datetime(2026, 11, 9, 12), 70.0)], available=False
    )
    # A keyword-alert listing: no book, never public.
    db.add(ProductModel(url="https://olx/x", title="1984 usado", source_website_id=EV))
    db.commit()
    return BookCatalogRepository(db)


class TestSearch:
    def test_finds_by_author_ignoring_case_and_accents(self, catalog):
        books, total = catalog.search("MARQUEZ", 20, 0)

        assert [b.title for b in books] == ["Cem anos de solidão"]
        assert total == 1

    def test_finds_by_title_with_accents_typed_without(self, catalog):
        books, _ = catalog.search("solidao", 20, 0)

        assert [b.isbn13 for b in books] == ["9788501012074"]

    def test_does_not_search_the_synopsis(self, catalog):
        assert catalog.search("piloto", 20, 0) == ([], 0)

    def test_books_in_stock_come_first(self, catalog):
        books, total = catalog.search("orwell", 20, 0)

        assert [b.title for b in books] == ["1984", "A revolução dos bichos"]
        assert total == 2
        assert (books[0].lowest_new, books[0].lowest_used) == (49.9, 20.0)
        assert books[0].offer_count == 3
        assert books[1].offer_count == 0

    def test_pages(self, catalog):
        books, total = catalog.search("orwell", 1, 1)

        assert [b.title for b in books] == ["A revolução dos bichos"]
        assert total == 2

    def test_a_wildcard_in_the_term_is_literal(self, catalog):
        assert catalog.search("%", 20, 0) == ([], 0)


class TestGetBook:
    def test_has_every_offer_with_its_latest_price(self, catalog):
        book = catalog.get_book("9788535914849")

        assert book.attributes["authors"] == ["George Orwell"]
        assert [(o.store, o.condition, o.price) for o in book.offers] == [
            ("estante_virtual", ProductCondition.USED, 20.0),
            ("livraria_da_vila", ProductCondition.NEW, 49.9),
            ("estante_virtual", ProductCondition.NEW, 55.0),
        ]
        assert book.offers[1].last_checked_at == datetime(2026, 11, 10, 2, tzinfo=UTC)

    def test_out_of_stock_offers_come_last(self, catalog):
        book = catalog.get_book("9788501012074")

        assert [o.is_available for o in book.offers] == [True, False]

    def test_unknown_isbn(self, catalog):
        assert catalog.get_book("9780306406157") is None


class TestDailyLows:
    def test_lowest_per_brazil_day_and_condition(self, catalog):
        lows = catalog.daily_lows("9788535914849", datetime(2026, 11, 1, tzinfo=UTC))

        assert [(low.day, low.condition, low.price) for low in lows] == [
            (date(2026, 11, 8), ProductCondition.NEW, 60.0),
            # 01:00 and 02:00 UTC on the 10th are still the 9th in Brazil
            (date(2026, 11, 9), ProductCondition.NEW, 49.9),
            (date(2026, 11, 9), ProductCondition.USED, 20.0),
        ]

    def test_points_before_the_window_are_left_out(self, catalog):
        lows = catalog.daily_lows("9788535914849", datetime(2026, 11, 9, tzinfo=UTC))

        assert date(2026, 11, 8) not in {low.day for low in lows}

    def test_unknown_isbn(self, catalog):
        assert (
            catalog.daily_lows("9780306406157", datetime(2026, 1, 1, tzinfo=UTC)) == []
        )
