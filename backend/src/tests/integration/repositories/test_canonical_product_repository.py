"""
Integration tests for CanonicalProductRepository and the offer link.

Uses SQLite in-memory, like the other repository tests.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.catalog.entities import (
    CanonicalProduct,
    IdentifierKind,
    ProductCategory,
    ProductIdentifier,
)
from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.persistence.models import (  # noqa: F401
    CanonicalProduct as CanonicalProductModel,
)
from src.app.catalog.persistence.models import PriceHistory as PriceHistoryModel
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.catalog.persistence.models import (  # noqa: F401
    ProductIdentifier as ProductIdentifierModel,
)
from src.app.catalog.persistence.repositories import (
    CanonicalProductRepository,
    ProductRepository,
)
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.database_config import Base

ISBN13 = "9788535914849"


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def a_book(isbn=ISBN13, title="1984"):
    return CanonicalProduct(
        category=ProductCategory.BOOK,
        title=title,
        attributes={"authors": ["George Orwell"], "year": 2009},
        identifiers=[ProductIdentifier(kind=IdentifierKind.ISBN13, value=isbn)],
    )


class TestCanonicalProductRepository:
    def test_create_stores_the_product_and_its_identifiers(self, db):
        created = CanonicalProductRepository(db).create(a_book())

        assert created.id is not None
        assert created.category == ProductCategory.BOOK
        assert created.attributes == {"authors": ["George Orwell"], "year": 2009}
        assert len(created.identifiers) == 1
        assert created.identifiers[0].id is not None
        assert created.identifiers[0].value == ISBN13

    def test_get_by_identifier_finds_the_product(self, db):
        repo = CanonicalProductRepository(db)
        created = repo.create(a_book())

        found = repo.get_by_identifier(IdentifierKind.ISBN13, ISBN13)

        assert found.id == created.id
        assert found.title == "1984"

    def test_get_by_identifier_returns_none_for_an_unknown_code(self, db):
        repo = CanonicalProductRepository(db)
        repo.create(a_book())

        assert repo.get_by_identifier(IdentifierKind.ISBN13, "9780306406157") is None

    def test_creating_the_same_isbn_twice_returns_the_first_product(self, db):
        repo = CanonicalProductRepository(db)
        first = repo.create(a_book(title="1984"))

        second = repo.create(a_book(title="1984 (duplicate)"))

        assert second.id == first.id
        assert second.title == "1984"
        assert db.query(CanonicalProductModel).count() == 1

    def test_the_repository_is_usable_after_a_duplicate(self, db):
        repo = CanonicalProductRepository(db)
        repo.create(a_book())
        repo.create(a_book())

        other = repo.create(a_book(isbn="9780306406157", title="Other"))

        assert other.title == "Other"
        assert db.query(CanonicalProductModel).count() == 2


class TestOfferLink:
    def test_an_offer_keeps_the_canonical_product_it_points_to(self, db):
        db.add(
            SourceWebsiteModel(
                id=1, name="Estante Virtual", base_url="https://estantevirtual.com.br"
            )
        )
        db.commit()
        book = CanonicalProductRepository(db).create(a_book())
        products = ProductRepository(db)

        created = products.create(
            ProductEntity(
                url="https://estantevirtual.com.br/livro/1984",
                title="1984",
                source_website_id=1,
                canonical_product_id=book.id,
            )
        )

        assert products.get_by_id(created.id).canonical_product_id == book.id

    def test_offers_without_a_canonical_product_still_work(self, db):
        db.add(
            SourceWebsiteModel(
                id=1, name="Estante Virtual", base_url="https://estantevirtual.com.br"
            )
        )
        db.commit()
        products = ProductRepository(db)

        created = products.create(
            ProductEntity(
                url="https://estantevirtual.com.br/livro/x",
                title="x",
                source_website_id=1,
            )
        )

        assert products.get_by_id(created.id).canonical_product_id is None


class TestListByStaleness:
    """The collection queue: never-priced books first, then the oldest point."""

    STORE, OTHER_STORE = 1, 2

    @pytest.fixture
    def stores(self, db):
        db.add_all(
            [
                SourceWebsiteModel(id=self.STORE, name="a", base_url="https://a"),
                SourceWebsiteModel(id=self.OTHER_STORE, name="b", base_url="https://b"),
            ]
        )
        db.commit()

    def price_at(self, db, book, store, *days_ago):
        """An offer for the book at the store, with one price point per day given."""
        offer = ProductModel(
            url=f"https://{store}/{book.id}/{len(days_ago)}",
            title=book.title,
            source_website_id=store,
            canonical_product_id=book.id,
        )
        db.add(offer)
        db.flush()
        now = datetime(2026, 11, 10, 12, 0)
        db.add_all(
            PriceHistoryModel(
                product_id=offer.id, price=10, created_at=now - timedelta(days=d)
            )
            for d in days_ago
        )
        db.commit()

    def test_orders_never_priced_first_then_oldest_point(self, db, stores):
        repo = CanonicalProductRepository(db)
        fresh = repo.create(a_book(isbn="9780000000002", title="fresh"))
        stale = repo.create(a_book(isbn="9780000000001", title="stale"))
        never = repo.create(a_book(isbn="9780000000003", title="never"))
        self.price_at(db, fresh, self.STORE, 5, 0)  # latest point counts: today
        self.price_at(db, stale, self.STORE, 3)
        self.price_at(db, never, self.OTHER_STORE, 9)  # another store's point

        queue = repo.list_by_staleness(IdentifierKind.ISBN13, self.STORE)

        assert [q.value for q in queue] == [
            "9780000000003",
            "9780000000001",
            "9780000000002",
        ]
        assert queue[0].last_checked_at is None
        assert queue[1].last_checked_at == datetime(2026, 11, 7, 12, 0)

    def test_uses_the_latest_point_across_the_books_offers(self, db, stores):
        repo = CanonicalProductRepository(db)
        book = repo.create(a_book())
        self.price_at(db, book, self.STORE, 8)  # used offer, old
        self.price_at(db, book, self.STORE, 1, 2)  # new offer, recent

        (item,) = repo.list_by_staleness(IdentifierKind.ISBN13, self.STORE)

        assert item.last_checked_at == datetime(2026, 11, 9, 12, 0)
