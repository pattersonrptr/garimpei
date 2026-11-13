"""Characterization tests for GET /price-alerts/{id}/products.

Written Nov 12, 2026, before moving the search behind this endpoint from
alerts to catalog: they pin which listings it returns, with and without
the alert's max price, and in which order.
"""

import pytest

from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.alerts.persistence.models import price_alert_source_website
from src.app.catalog.entities import ProductCondition
from src.app.catalog.persistence.models import PriceHistory as PriceHistoryModel
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)


def a_listing(test_db, title, price, store_id, available=True):
    listing = ProductModel(
        url=f"https://test.example.com/{title.replace(' ', '-').lower()}",
        title=title,
        condition=ProductCondition.NEW,
        is_available=available,
        source_website_id=store_id,
    )
    test_db.add(listing)
    test_db.commit()
    test_db.add(PriceHistoryModel(product_id=listing.id, price=price))
    test_db.commit()
    return listing


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
    """Matching listings at 800, 200 and 450, plus ones the alert never shows."""
    store = sample_source_website.id
    other_store = SourceWebsiteModel(name="Other", base_url="https://other.example")
    test_db.add(other_store)
    test_db.commit()
    a_listing(test_db, "Premium Headphones", 800.0, store)
    a_listing(test_db, "Budget Headphones", 200.0, store)
    a_listing(test_db, "Studio Headphones", 450.0, store)
    a_listing(test_db, "Sold Headphones", 100.0, store, available=False)
    a_listing(test_db, "Other Store Headphones", 100.0, other_store.id)
    a_listing(test_db, "Bluetooth Speaker", 100.0, store)


def titles(response):
    return [item["attributes"]["title"] for item in response.json()["data"]]


def test_lists_the_alerts_matches_at_or_under_its_max_price_cheapest_first(
    client, auth_headers, alert, listings
):
    response = client.get(f"/price-alerts/{alert.id}/products", headers=auth_headers)

    assert response.status_code == 200
    assert titles(response) == ["Budget Headphones", "Studio Headphones"]
    assert response.json()["meta"]["total"] == 2


def test_without_the_max_price_filter_lists_every_match_cheapest_first(
    client, auth_headers, alert, listings
):
    response = client.get(
        f"/price-alerts/{alert.id}/products?filter_by_max_price=false",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert titles(response) == [
        "Budget Headphones",
        "Studio Headphones",
        "Premium Headphones",
    ]


def test_pages_through_the_matches(client, auth_headers, alert, listings):
    response = client.get(
        f"/price-alerts/{alert.id}/products?filter_by_max_price=false&limit=1&offset=1",
        headers=auth_headers,
    )

    assert titles(response) == ["Studio Headphones"]
    assert response.json()["meta"]["total"] == 3


def test_unknown_alert_is_not_found(client, auth_headers):
    response = client.get("/price-alerts/9999/products", headers=auth_headers)

    assert response.status_code == 404
