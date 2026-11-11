"""Book alerts end to end (Phase 4c): create an alert on a book by ISBN, then
an offer for that book at or under the price sends the e-mail."""

from unittest.mock import MagicMock

import pytest

from src.app.alerts.persistence.models import NotificationLog as NotificationLogModel
from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.catalog.entities import BookMetadata
from src.app.catalog.http.offer_controller import get_book_metadata_gateway
from src.app.catalog.ports import BookMetadataGateway
from src.app.infrastructure.services.email_service import get_email_service
from src.app.interfaces.services.email_service import EmailResult
from src.main import app

ISBN13 = "9788535914849"


class StubMetadata(BookMetadataGateway):
    def fetch(self, isbn13):
        return BookMetadata(isbn13=ISBN13, title="1984", authors=("Orwell",))


@pytest.fixture
def email():
    service = MagicMock()
    service.send_price_alert_email.return_value = EmailResult(
        success=True, status_code=202
    )
    app.dependency_overrides[get_email_service] = lambda: service
    app.dependency_overrides[get_book_metadata_gateway] = StubMetadata
    return service


def ingest(client, headers, store_id, price, condition="used", url=None):
    response = client.post(
        "/offers/",
        json={
            "data": {
                "type": "offers",
                "attributes": {
                    "isbn": ISBN13,
                    "source_website_id": store_id,
                    "url": url or f"https://store/{condition}/{price}",
                    "price": price,
                    "condition": condition,
                },
            }
        },
        headers=headers,
    )
    assert response.status_code in (200, 201), response.json()
    return response


def create_alert(client, headers, user_id, max_price, condition="used", isbn=ISBN13):
    return client.post(
        "/price-alerts/",
        json={
            "data": {
                "type": "price_alert",
                "attributes": {
                    "isbn": isbn,
                    "condition": condition,
                    "max_price": max_price,
                    "user_id": user_id,
                },
            }
        },
        headers=headers,
    )


@pytest.fixture
def book(client, staff_auth_headers, sample_source_website, email):
    """The book exists in the catalog with a used offer at R$ 28.50."""
    ingest(client, staff_auth_headers, sample_source_website.id, 28.5)


class TestCreateBookAlert:
    def test_creates_an_alert_on_the_book_without_a_search_config(
        self, client, auth_headers, sample_user, book, test_db
    ):
        response = create_alert(client, auth_headers, sample_user.id, 20)

        assert response.status_code == 201, response.json()
        attributes = response.json()["data"]["attributes"]
        assert attributes["search_term"] == "1984"
        assert attributes["condition"] == "used"
        assert attributes["canonical_product_id"] is not None
        assert attributes["source_website_ids"] == []
        # the old keyword scrapers must not start searching the title
        assert attributes["search_config_id"] is None

    def test_an_isbn_10_finds_the_same_book(
        self, client, auth_headers, sample_user, book
    ):
        response = create_alert(
            client, auth_headers, sample_user.id, 20, isbn="8535914846"
        )

        assert response.status_code == 201

    def test_condition_defaults_to_any(self, client, auth_headers, sample_user, book):
        response = create_alert(
            client, auth_headers, sample_user.id, 20, condition=None
        )

        assert response.json()["data"]["attributes"]["condition"] == "any"

    def test_an_offer_already_under_the_price_is_sent_at_once(
        self, client, auth_headers, sample_user, book, email
    ):
        create_alert(client, auth_headers, sample_user.id, 30)

        email.send_price_alert_email.assert_called_once()
        assert email.send_price_alert_email.call_args.kwargs["product_price"] == 28.5

    def test_unknown_book_is_404(self, client, auth_headers, sample_user, email):
        response = create_alert(
            client, auth_headers, sample_user.id, 20, isbn="9780000000002"
        )

        assert response.status_code == 404
        assert response.json()["errors"][0]["code"] == "BOOK_NOT_FOUND"

    def test_one_alert_per_book_and_condition(
        self, client, auth_headers, sample_user, book
    ):
        assert create_alert(client, auth_headers, sample_user.id, 20).status_code == 201
        again = create_alert(client, auth_headers, sample_user.id, 15)
        other_condition = create_alert(client, auth_headers, sample_user.id, 60, "new")

        assert again.status_code == 409
        assert again.json()["errors"][0]["code"] == "DUPLICATE_BOOK_ALERT"
        assert other_condition.status_code == 201

    def test_isbn_and_search_term_together_are_refused(
        self, client, auth_headers, sample_user, book
    ):
        response = client.post(
            "/price-alerts/",
            json={
                "data": {
                    "type": "price_alert",
                    "attributes": {
                        "isbn": ISBN13,
                        "search_term": "1984",
                        "max_price": 20,
                        "user_id": sample_user.id,
                    },
                }
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestIngestingOffersChecksBookAlerts:
    def test_an_offer_under_the_price_sends_the_email(
        self,
        client,
        auth_headers,
        staff_auth_headers,
        sample_user,
        sample_source_website,
        book,
        email,
        test_db,
    ):
        create_alert(client, auth_headers, sample_user.id, 20)
        email.send_price_alert_email.assert_not_called()  # R$ 28.50 is too much

        ingest(client, staff_auth_headers, sample_source_website.id, 19.9)

        email.send_price_alert_email.assert_called_once()
        sent = email.send_price_alert_email.call_args.kwargs
        assert sent["product_price"] == 19.9
        assert sent["to_email"] == sample_user.email
        assert test_db.query(NotificationLogModel).count() == 1

    def test_the_same_offer_is_not_sent_twice(
        self,
        client,
        auth_headers,
        staff_auth_headers,
        sample_user,
        sample_source_website,
        book,
        email,
    ):
        create_alert(client, auth_headers, sample_user.id, 20)
        ingest(
            client,
            staff_auth_headers,
            sample_source_website.id,
            19.9,
            url="https://s/a",
        )
        ingest(
            client,
            staff_auth_headers,
            sample_source_website.id,
            19.5,
            url="https://s/a",
        )

        assert email.send_price_alert_email.call_count == 1

    def test_an_offer_in_another_condition_is_ignored(
        self,
        client,
        auth_headers,
        staff_auth_headers,
        sample_user,
        sample_source_website,
        book,
        email,
    ):
        create_alert(client, auth_headers, sample_user.id, 20, condition="used")

        ingest(
            client, staff_auth_headers, sample_source_website.id, 15, condition="new"
        )

        email.send_price_alert_email.assert_not_called()

    def test_a_paused_alert_sends_nothing(
        self,
        client,
        auth_headers,
        staff_auth_headers,
        sample_user,
        sample_source_website,
        book,
        email,
        test_db,
    ):
        create_alert(client, auth_headers, sample_user.id, 20)
        test_db.query(PriceAlertModel).update({"is_active": False})
        test_db.commit()

        ingest(client, staff_auth_headers, sample_source_website.id, 10)

        email.send_price_alert_email.assert_not_called()

    def test_an_alert_failure_does_not_fail_the_ingestion(
        self,
        client,
        auth_headers,
        staff_auth_headers,
        sample_user,
        sample_source_website,
        book,
        email,
    ):
        create_alert(client, auth_headers, sample_user.id, 20)
        email.send_price_alert_email.side_effect = RuntimeError("smtp down")

        response = ingest(client, staff_auth_headers, sample_source_website.id, 10)

        assert response.status_code == 201
