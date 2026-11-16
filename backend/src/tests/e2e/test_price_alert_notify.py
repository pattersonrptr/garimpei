"""
Characterization tests for POST /price-alerts/{id}/notify (staff only).

They pin today's behavior before the endpoint's wiring moves to
alerts/wiring.py: the owner gets one e-mail about the cheapest listing at or
under the max price, from the alert's stores, named after its store.
Alerts are created before their listings so the "alert changed" check finds
nothing and does not use up the rate limit.
"""

from unittest.mock import MagicMock

import pytest

from src.app.catalog.persistence.models import PriceHistory as PriceHistoryModel
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.infrastructure.services.email_service import get_email_service
from src.app.interfaces.services.email_service import EmailResult
from src.main import app


@pytest.fixture
def email_service():
    """Record the alert e-mails instead of sending them."""
    service = MagicMock()
    service.send_price_alert_email.return_value = EmailResult(success=True)
    app.dependency_overrides[get_email_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_email_service, None)


@pytest.fixture
def alert(client, staff_auth_headers, sample_user, sample_source_website):
    """An alert for "clean code" up to R$ 50, owned by sample_user."""
    response = client.post(
        "/price-alerts/",
        json={
            "data": {
                "type": "price_alert",
                "attributes": {
                    "search_term": "clean code",
                    "max_price": 50,
                    "user_id": sample_user.id,
                    "frequency_minutes": 360,
                    "source_website_ids": [sample_source_website.id],
                },
            }
        },
        headers=staff_auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def add_listing(test_db, site, title, price):
    product = ProductModel(
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        title=title,
        is_available=True,
        source_website_id=site.id,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)
    test_db.add(PriceHistoryModel(product_id=product.id, price=price))
    test_db.commit()
    return product


def notify(client, headers, alert_id):
    return client.post(f"/price-alerts/{alert_id}/notify", headers=headers)


def result(response):
    assert response.status_code == 200, response.text
    return response.json()["data"]["attributes"]


class TestNotifyPriceAlert:
    def test_owner_is_emailed_the_cheapest_listing_under_max_price(
        self,
        client,
        staff_auth_headers,
        sample_source_website,
        test_db,
        email_service,
        alert,
    ):
        add_listing(test_db, sample_source_website, "Clean Code capa dura", 45)
        cheapest = add_listing(test_db, sample_source_website, "Clean Code bolso", 30)
        add_listing(test_db, sample_source_website, "Clean Code autografado", 80)

        attributes = result(notify(client, staff_auth_headers, alert["id"]))

        assert attributes["status"] == "sent"
        assert attributes["notifications_sent"] == 1
        email_service.send_price_alert_email.assert_called_once_with(
            to_email="test@example.com",
            search_term="clean code",
            product_title="Clean Code bolso",
            product_price=30.0,
            max_price=50.0,
            product_url=cheapest.url,
            source_website_name="Test Website",
        )

    def test_nothing_is_sent_when_no_listing_is_under_max_price(
        self,
        client,
        staff_auth_headers,
        sample_source_website,
        test_db,
        email_service,
        alert,
    ):
        add_listing(test_db, sample_source_website, "Clean Code autografado", 80)

        attributes = result(notify(client, staff_auth_headers, alert["id"]))

        assert attributes["status"] == "skipped"
        assert attributes["notifications_sent"] == 0
        email_service.send_price_alert_email.assert_not_called()

    def test_a_second_notification_within_the_rate_limit_is_skipped(
        self,
        client,
        staff_auth_headers,
        sample_source_website,
        test_db,
        email_service,
        alert,
    ):
        add_listing(test_db, sample_source_website, "Clean Code bolso", 30)
        notify(client, staff_auth_headers, alert["id"])

        attributes = result(notify(client, staff_auth_headers, alert["id"]))

        assert attributes["status"] == "skipped"
        assert attributes["message"].startswith("Rate limited")
        email_service.send_price_alert_email.assert_called_once()

    def test_unknown_alert_is_not_found(self, client, staff_auth_headers):
        response = notify(client, staff_auth_headers, 999999)

        assert response.status_code == 404
