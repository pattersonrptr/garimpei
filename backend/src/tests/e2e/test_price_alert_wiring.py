"""Characterization tests for how the price alert endpoints are wired.

Written Nov 13, 2026, before moving the alerts controller's wiring to
``alerts/wiring.py``. A mutation check found three wirings no test caught:
``POST /price-alerts/{id}/notify`` sending through the real e-mail service
instead of the injected one, the same endpoint finding no listing, and
``DELETE /price-alerts/{id}`` leaving its search running.
"""

from unittest.mock import MagicMock

import pytest

from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.alerts.persistence.models import price_alert_source_website
from src.app.catalog.entities import ProductCondition
from src.app.catalog.persistence.models import PriceHistory as PriceHistoryModel
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.services.email_service import get_email_service
from src.app.interfaces.services.email_service import EmailResult
from src.main import app


def a_listing(test_db, title, price, store_id):
    listing = ProductModel(
        url=f"https://test.example.com/{title.replace(' ', '-').lower()}",
        title=title,
        condition=ProductCondition.NEW,
        is_available=True,
        source_website_id=store_id,
    )
    test_db.add(listing)
    test_db.commit()
    test_db.add(PriceHistoryModel(product_id=listing.id, price=price))
    test_db.commit()
    return listing


@pytest.fixture
def mailer():
    """The e-mail service the endpoints get, recording what they send."""
    service = MagicMock()
    service.send_price_alert_email.return_value = EmailResult(
        success=True, status_code=202
    )
    app.dependency_overrides[get_email_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_email_service, None)


@pytest.fixture
def alert(test_db, sample_user, sample_source_website):
    """A keyword alert on "headphones", max R$ 500, watching one store."""
    alert = PriceAlertModel(
        search_term="headphones",
        max_price=500.0,
        is_active=True,
        frequency_minutes=60,
        user_id=sample_user.id,
    )
    test_db.add(alert)
    test_db.commit()
    test_db.execute(
        price_alert_source_website.insert().values(
            price_alert_id=alert.id, source_website_id=sample_source_website.id
        )
    )
    test_db.commit()
    return alert


@pytest.fixture
def listings(test_db, sample_source_website):
    """Matches at 800, 450 and 200 in the alert's store, 100 in another."""
    store = sample_source_website.id
    other_store = SourceWebsiteModel(name="Other", base_url="https://other.example")
    test_db.add(other_store)
    test_db.commit()
    a_listing(test_db, "Premium Headphones", 800.0, store)
    a_listing(test_db, "Studio Headphones", 450.0, store)
    a_listing(test_db, "Budget Headphones", 200.0, store)
    a_listing(test_db, "Other Store Headphones", 100.0, other_store.id)


def test_notify_emails_the_owner_the_cheapest_match_under_the_max_price(
    client,
    staff_auth_headers,
    mailer,
    alert,
    listings,
    sample_user,
    sample_source_website,
):
    response = client.post(
        f"/price-alerts/{alert.id}/notify", headers=staff_auth_headers
    )

    assert response.status_code == 200
    result = response.json()["data"]["attributes"]
    assert result["status"] == "sent"
    assert result["notifications_sent"] == 1
    mailer.send_price_alert_email.assert_called_once()
    sent = mailer.send_price_alert_email.call_args.kwargs
    assert sent["to_email"] == sample_user.email
    assert sent["search_term"] == "headphones"
    assert sent["product_title"] == "Budget Headphones"
    assert sent["product_price"] == 200.0
    assert sent["max_price"] == 500.0
    assert sent["source_website_name"] == sample_source_website.name


def test_deleting_the_only_alert_of_a_search_stops_the_search(
    client, auth_headers, sample_user, sample_source_website
):
    created = client.post(
        "/price-alerts/",
        json={
            "data": {
                "type": "price_alert",
                "attributes": {
                    "search_term": "headphones",
                    "max_price": 500,
                    "user_id": sample_user.id,
                    "frequency_minutes": 1440,
                    "source_website_ids": [sample_source_website.id],
                },
            }
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    alert = created.json()["data"]
    search = f"/search-configs/{alert['attributes']['search_config_id']}"
    assert client.get(search, headers=auth_headers).json()["data"]["attributes"][
        "is_active"
    ]

    deleted = client.delete(f"/price-alerts/{alert['id']}", headers=auth_headers)

    assert deleted.status_code == 204
    after = client.get(search, headers=auth_headers)
    assert after.status_code == 200
    assert after.json()["data"]["attributes"]["is_active"] is False
