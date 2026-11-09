"""
Integration tests for CanonicalProductRepository and the offer link.

Uses SQLite in-memory, like the other repository tests.
"""

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
