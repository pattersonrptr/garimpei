"""POST /offers end to end (FastAPI + SQLite), with a fake book metadata source."""

import pytest

from src.app.catalog.entities import BookMetadata
from src.app.catalog.http.offer_controller import get_book_metadata_gateway
from src.app.catalog.persistence.models import (
    CanonicalProduct as CanonicalProductModel,
)
from src.app.catalog.persistence.models import PriceHistory as PriceHistoryModel
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.catalog.persistence.models import (
    ProductIdentifier as ProductIdentifierModel,
)
from src.app.catalog.ports import BookMetadataGateway, BookMetadataUnavailableError
from src.main import app

ISBN13 = "9788535914849"
OTHER_ISBN = "9788576573135"
URL = "https://www.estantevirtual.com.br/livro/1984-usado-123"


class StubMetadata(BookMetadataGateway):
    def __init__(self, book=None, error=None):
        self.book, self.error = book, error

    def fetch(self, isbn13):
        if self.error:
            raise self.error
        return self.book


@pytest.fixture
def use_metadata():
    """Install a metadata stub for the request; removed with the client fixture."""

    def install(stub):
        app.dependency_overrides[get_book_metadata_gateway] = lambda: stub

    return install


@pytest.fixture
def known_book(use_metadata):
    use_metadata(
        StubMetadata(BookMetadata(isbn13=ISBN13, title="1984", authors=("Orwell",)))
    )


def payload(source_website_id, **changes):
    attributes = {
        "isbn": "978-85-359-1484-9",
        "source_website_id": source_website_id,
        "url": URL,
        "price": 28.5,
        "condition": "used",
        "city": "São Paulo",
        "state": "SP",
    }
    attributes.update(changes)
    return {"data": {"type": "offers", "attributes": attributes}}


class TestIngestOffer:
    def test_new_offer_returns_201_linked_to_the_book(
        self, client, staff_auth_headers, sample_source_website, known_book, test_db
    ):
        response = client.post(
            "/offers/",
            json=payload(sample_source_website.id),
            headers=staff_auth_headers,
        )

        assert response.status_code == 201
        attributes = response.json()["data"]["attributes"]
        assert attributes["title"] == "1984"
        assert attributes["condition"] == "used"
        assert attributes["current_price"] == 28.5
        assert attributes["last_checked_at"].endswith("Z")  # UTC, explicit
        book = test_db.query(CanonicalProductModel).one()
        assert attributes["canonical_product_id"] == book.id

    def test_same_url_again_returns_200_and_adds_history(
        self, client, staff_auth_headers, sample_source_website, known_book, test_db
    ):
        client.post(
            "/offers/",
            json=payload(sample_source_website.id, price=28.5),
            headers=staff_auth_headers,
        )

        response = client.post(
            "/offers/",
            json=payload(sample_source_website.id, price=26.0),
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["data"]["attributes"]["current_price"] == 26.0
        assert test_db.query(ProductModel).count() == 1
        assert test_db.query(CanonicalProductModel).count() == 1
        prices = [float(p.price) for p in test_db.query(PriceHistoryModel).all()]
        assert prices == [28.5, 26.0]

    def test_regular_users_cannot_ingest(
        self, client, auth_headers, sample_source_website, known_book
    ):
        response = client.post(
            "/offers/", json=payload(sample_source_website.id), headers=auth_headers
        )

        assert response.status_code == 403

    def test_anonymous_requests_are_rejected(
        self, client, sample_source_website, known_book
    ):
        response = client.post("/offers/", json=payload(sample_source_website.id))

        # FastAPI's HTTPBearer answers 403 when no token is sent (same as the
        # other endpoints' tests accept).
        assert response.status_code in (401, 403)

    def test_invalid_isbn_returns_422(
        self, client, staff_auth_headers, sample_source_website, known_book, test_db
    ):
        response = client.post(
            "/offers/",
            json=payload(sample_source_website.id, isbn="9788535914848"),
            headers=staff_auth_headers,
        )

        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "INVALID_ISBN"
        assert test_db.query(ProductModel).count() == 0

    def test_unknown_book_returns_422(
        self, client, staff_auth_headers, sample_source_website, use_metadata
    ):
        use_metadata(StubMetadata(book=None))

        response = client.post(
            "/offers/",
            json=payload(sample_source_website.id),
            headers=staff_auth_headers,
        )

        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "UNKNOWN_ISBN"

    def test_unknown_store_returns_422(
        self, client, staff_auth_headers, sample_source_website, known_book
    ):
        response = client.post(
            "/offers/", json=payload(9999), headers=staff_auth_headers
        )

        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "UNKNOWN_SOURCE_WEBSITE"

    def test_non_positive_price_is_rejected(
        self, client, staff_auth_headers, sample_source_website, known_book, test_db
    ):
        response = client.post(
            "/offers/",
            json=payload(sample_source_website.id, price=0),
            headers=staff_auth_headers,
        )

        assert response.status_code == 422
        assert test_db.query(ProductModel).count() == 0

    def test_metadata_source_down_returns_503(
        self, client, staff_auth_headers, sample_source_website, use_metadata, test_db
    ):
        use_metadata(StubMetadata(error=BookMetadataUnavailableError("timeout")))

        response = client.post(
            "/offers/",
            json=payload(sample_source_website.id),
            headers=staff_auth_headers,
        )

        assert response.status_code == 503
        assert response.json()["errors"][0]["code"] == "METADATA_UNAVAILABLE"
        assert test_db.query(ProductModel).count() == 0


class TestCollectionQueue:
    def test_lists_books_the_store_never_priced_before_priced_ones(
        self, client, staff_auth_headers, sample_source_website, known_book, test_db
    ):
        test_db.add(
            CanonicalProductModel(
                category="book",
                title="Duna",
                attributes={},
                identifiers=[ProductIdentifierModel(kind="isbn13", value=OTHER_ISBN)],
            )
        )
        test_db.commit()
        client.post(
            "/offers/",
            json=payload(sample_source_website.id),
            headers=staff_auth_headers,
        )

        response = client.get(
            "/offers/collection-queue",
            params={"store": sample_source_website.name},
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        items = response.json()["data"]
        assert [i["attributes"]["isbn"] for i in items] == [OTHER_ISBN, ISBN13]
        assert items[0]["attributes"]["last_checked_at"] is None
        assert items[1]["attributes"]["last_checked_at"] is not None

    def test_unknown_store_returns_404(self, client, staff_auth_headers):
        response = client.get(
            "/offers/collection-queue",
            params={"store": "nowhere"},
            headers=staff_auth_headers,
        )

        assert response.status_code == 404
        assert response.json()["errors"][0]["code"] == "UNKNOWN_SOURCE_WEBSITE"

    def test_requires_staff(self, client, auth_headers, sample_source_website):
        response = client.get(
            "/offers/collection-queue",
            params={"store": sample_source_website.name},
            headers=auth_headers,
        )

        assert response.status_code == 403
