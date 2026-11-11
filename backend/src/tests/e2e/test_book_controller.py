"""Public /books endpoints end to end (FastAPI + SQLite), with no login."""

from datetime import UTC, datetime

import pytest

from src.app.catalog.entities import (
    CanonicalProduct,
    IdentifierKind,
    ProductCategory,
    ProductIdentifier,
)
from src.app.catalog.persistence.models import PriceHistory as PriceHistoryModel
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.catalog.persistence.repositories import CanonicalProductRepository

ISBN13 = "9788535914849"


@pytest.fixture
def book_with_offer(test_db, sample_source_website):
    book = CanonicalProductRepository(test_db).create(
        CanonicalProduct(
            category=ProductCategory.BOOK,
            title="1984",
            attributes={"authors": ["George Orwell"], "publisher": "Companhia"},
            identifiers=[ProductIdentifier(kind=IdentifierKind.ISBN13, value=ISBN13)],
        )
    )
    offer = ProductModel(
        url="https://ev/1984?condition=usado",
        title="1984",
        source_website_id=sample_source_website.id,
        condition="used",
        canonical_product_id=book.id,
    )
    test_db.add(offer)
    test_db.flush()
    test_db.add(
        PriceHistoryModel(
            product_id=offer.id,
            price=17.5,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    test_db.commit()
    return book


class TestPublicBooks:
    def test_search_needs_no_login(self, client, book_with_offer):
        response = client.get("/books/", params={"q": "orwell"})

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] == 1
        book = body["data"][0]
        assert book["id"] == ISBN13
        assert book["attributes"]["lowest_used"] == 17.5
        assert book["attributes"]["lowest_new"] is None

    def test_book_page_has_offers(self, client, book_with_offer):
        response = client.get("/books/978-85-359-1484-9")

        assert response.status_code == 200
        attributes = response.json()["data"]["attributes"]
        assert attributes["publisher"] == "Companhia"
        (offer,) = attributes["offers"]
        assert offer["store"] == "Test Website"
        assert offer["condition"] == "used"
        assert offer["price"] == 17.5
        assert offer["last_checked_at"].endswith("+00:00")

    def test_book_page_has_a_verdict_per_condition(self, client, book_with_offer):
        attributes = client.get(f"/books/{ISBN13}").json()["data"]["attributes"]

        verdicts = {v["condition"]: v for v in attributes["verdicts"]}
        assert verdicts["used"]["status"] == "learning"  # one day of history
        assert verdicts["used"]["current"] == 17.5
        assert verdicts["used"]["days"] == 1
        assert verdicts["new"]["status"] == "no_offer"

    def test_unknown_or_invalid_isbn_is_404(self, client, book_with_offer):
        assert client.get("/books/9780306406157").status_code == 404
        assert client.get("/books/not-an-isbn").status_code == 404

    def test_price_history_has_daily_lows(self, client, book_with_offer):
        response = client.get(f"/books/{ISBN13}/price-history", params={"days": 30})

        assert response.status_code == 200
        (low,) = response.json()["data"]
        assert (low["condition"], low["price"]) == ("used", 17.5)

    def test_page_size_over_the_cap_is_refused(self, client):
        assert client.get("/books/", params={"q": "x", "limit": 51}).status_code == 422


def test_index_lists_books_without_login(client, book_with_offer):
    response = client.get("/books/index")

    assert response.status_code == 200
    assert [b["id"] for b in response.json()["data"]] == [ISBN13]
