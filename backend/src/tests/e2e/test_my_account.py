"""Phase 5a: the user's own account and alerts (login by e-mail, /auth/me,
password change, GET /me/alerts)."""

from unittest.mock import MagicMock

import pytest

from src.app.catalog.entities import BookMetadata
from src.app.catalog.http.offer_controller import get_book_metadata_gateway
from src.app.catalog.ports import BookMetadataGateway
from src.app.infrastructure.services.email_service import get_email_service
from src.app.interfaces.services.email_service import EmailResult
from src.main import app

ISBN13 = "9788535914849"


def login(client, name, password="Test@1234"):
    return client.post("/auth/login", data={"username": name, "password": password})


class TestLoginByEmail:
    def test_logs_in_with_the_email(self, client, sample_user):
        response = login(client, "test@example.com")

        assert response.status_code == 200
        assert response.json()["data"]["attributes"]["access_token"]

    def test_the_email_ignores_case(self, client, sample_user):
        assert login(client, "  Test@Example.COM ").status_code == 200

    def test_the_username_still_works(self, client, sample_user):
        assert login(client, "testuser").status_code == 200

    def test_a_wrong_password_is_refused(self, client, sample_user):
        assert login(client, "test@example.com", "nope").status_code == 400


class TestMe:
    def test_returns_the_account_without_the_password(self, client, auth_headers):
        response = client.get("/auth/me", headers=auth_headers)

        assert response.status_code == 200
        attributes = response.json()["data"]["attributes"]
        assert attributes["username"] == "testuser"
        assert attributes["email"] == "test@example.com"
        assert "hashed_password" not in attributes

    def test_needs_a_login(self, client):
        assert client.get("/auth/me").status_code == 401  # no token


def password_change(current, new):
    return {
        "data": {
            "type": "password_change",
            "attributes": {"current_password": current, "new_password": new},
        }
    }


class TestPasswordChange:
    def test_changes_the_password(self, client, auth_headers):
        response = client.put(
            "/auth/password",
            json=password_change("Test@1234", "Nova@Senha1"),
            headers=auth_headers,
        )

        assert response.status_code == 204
        assert login(client, "testuser", "Nova@Senha1").status_code == 200
        assert login(client, "testuser", "Test@1234").status_code == 400

    def test_the_current_password_must_be_right(self, client, auth_headers):
        response = client.put(
            "/auth/password",
            json=password_change("errada", "Nova@Senha1"),
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["errors"][0]["code"] == "WRONG_PASSWORD"

    def test_the_new_password_needs_eight_characters(self, client, auth_headers):
        response = client.put(
            "/auth/password",
            json=password_change("Test@1234", "curta"),
            headers=auth_headers,
        )

        assert response.status_code == 422


class StubMetadata(BookMetadataGateway):
    def fetch(self, isbn13):
        return BookMetadata(
            isbn13=ISBN13, title="1984", authors=("Orwell",), cover_url="https://c/1984"
        )


@pytest.fixture
def email():
    service = MagicMock()
    service.send_price_alert_email.return_value = EmailResult(
        success=True, status_code=202
    )
    app.dependency_overrides[get_email_service] = lambda: service
    app.dependency_overrides[get_book_metadata_gateway] = StubMetadata
    return service


def ingest(client, headers, store_id, price, condition):
    response = client.post(
        "/offers/",
        json={
            "data": {
                "type": "offers",
                "attributes": {
                    "isbn": ISBN13,
                    "source_website_id": store_id,
                    "url": f"https://store/{condition}",
                    "price": price,
                    "condition": condition,
                },
            }
        },
        headers=headers,
    )
    assert response.status_code in (200, 201), response.json()


def create_alert(client, headers, user_id, **attributes):
    response = client.post(
        "/price-alerts/",
        json={
            "data": {
                "type": "price_alert",
                "attributes": {"user_id": user_id, **attributes},
            }
        },
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    return response.json()["data"]


class TestMyAlerts:
    @pytest.fixture
    def book(self, client, staff_auth_headers, sample_source_website, email):
        ingest(client, staff_auth_headers, sample_source_website.id, 28.5, "used")
        ingest(client, staff_auth_headers, sample_source_website.id, 50.0, "new")

    def test_lists_product_alerts_with_today_and_the_emails_sent(
        self, client, auth_headers, sample_user, book
    ):
        create_alert(
            client,
            auth_headers,
            sample_user.id,
            isbn=ISBN13,
            condition="used",
            max_price=30,
        )

        response = client.get("/me/alerts", headers=auth_headers)

        assert response.status_code == 200
        (item,) = response.json()["data"]
        attributes = item["attributes"]
        assert attributes["condition"] == "used"
        assert attributes["max_price"] == 30
        assert attributes["product"]["title"] == "1984"
        assert attributes["product"]["isbn13"] == ISBN13
        assert attributes["product"]["category"] == "book"
        assert attributes["today"]["price"] == 28.5
        assert attributes["today"]["condition"] == "used"
        assert attributes["today"]["verdict"] == "learning"
        # 28.50 <= 30: the e-mail went out when the alert was created
        assert attributes["notices"]["total"] == 1
        assert attributes["notices"]["recent"][0]["store"] == "Test Website"

    def test_any_condition_shows_the_cheapest(
        self, client, auth_headers, sample_user, book
    ):
        create_alert(
            client,
            auth_headers,
            sample_user.id,
            isbn=ISBN13,
            condition="any",
            max_price=10,
        )

        (item,) = client.get("/me/alerts", headers=auth_headers).json()["data"]

        assert item["attributes"]["today"]["condition"] == "used"
        assert item["attributes"]["notices"] == {"total": 0, "recent": []}

    def test_keyword_alerts_are_left_out(
        self, client, auth_headers, sample_user, sample_source_website, book
    ):
        create_alert(
            client,
            auth_headers,
            sample_user.id,
            search_term="orwell",
            max_price=30,
            frequency_minutes=1440,
            source_website_ids=[sample_source_website.id],
        )

        assert client.get("/me/alerts", headers=auth_headers).json()["data"] == []

    def test_needs_a_login(self, client):
        assert client.get("/me/alerts").status_code == 401  # no token
