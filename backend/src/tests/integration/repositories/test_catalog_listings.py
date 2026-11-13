"""Integration tests for CatalogListings (alerts' Listings port).

The adapter alerts uses to find the listings it sends to alert owners,
over the real catalog tables and an in-memory SQLite database.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.alerts.entities import Listing
from src.app.alerts.persistence.listings import CatalogListings
from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.catalog.entities import (
    CanonicalProduct,
    IdentifierKind,
    ProductCategory,
    ProductIdentifier,
)
from src.app.catalog.persistence.models import PriceHistory as PriceHistoryModel
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.catalog.persistence.repositories import CanonicalProductRepository

# Import all models to register with Base.metadata
from src.app.infrastructure.database import models  # noqa: F401
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.database.models.user_model import User
from src.app.infrastructure.database_config import Base

OLX, ENJOEI = 1, 2


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all(
        [
            SourceWebsiteModel(id=OLX, name="OLX", base_url="https://olx"),
            SourceWebsiteModel(id=ENJOEI, name="Enjoei", base_url="https://enjoei"),
        ]
    )
    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def listings(db):
    return CatalogListings(db)


def a_listing(
    db,
    title,
    store=OLX,
    prices=(),
    condition="used",
    available=True,
    book_id=None,
    url=None,
):
    """A listing with price points given as (naive UTC datetime, price)."""
    listing = ProductModel(
        url=url or f"https://store/{title}",
        title=title,
        source_website_id=store,
        condition=condition,
        is_available=available,
        canonical_product_id=book_id,
    )
    db.add(listing)
    db.flush()
    db.add_all(
        PriceHistoryModel(product_id=listing.id, price=price, created_at=moment)
        for moment, price in prices
    )
    db.commit()
    return listing


def priced(price):
    return [(datetime(2026, 11, 10, 12), price)]


def a_book(db, isbn, title):
    return CanonicalProductRepository(db).create(
        CanonicalProduct(
            category=ProductCategory.BOOK,
            title=title,
            attributes={"authors": ["George Orwell"]},
            identifiers=[ProductIdentifier(kind=IdentifierKind.ISBN13, value=isbn)],
        )
    )


def a_keyword_alert(db, search_term, max_price, stores):
    owner = User(
        username=f"owner-{search_term}",
        email=f"{search_term}@example.com",
        hashed_password="x",
        is_active=True,
    )
    db.add(owner)
    db.flush()
    alert = PriceAlertModel(search_term=search_term, max_price=max_price, user=owner)
    alert.source_websites = [db.get(SourceWebsiteModel, store) for store in stores]
    db.add(alert)
    db.commit()
    return alert


# get_by_id


def test_listing_carries_what_the_alert_email_needs(db, listings):
    saved = a_listing(
        db,
        "iPhone 13 128GB",
        store=ENJOEI,
        prices=priced(2500.0),
        condition="used",
        url="https://enjoei/iphone-13",
    )

    assert listings.get_by_id(saved.id) == Listing(
        id=saved.id,
        title="iPhone 13 128GB",
        url="https://enjoei/iphone-13",
        store_id=ENJOEI,
        price=2500.0,
        condition="used",
        is_available=True,
    )


def test_listing_price_is_its_latest_price_point(db, listings):
    saved = a_listing(
        db,
        "iPhone 13",
        prices=[
            (datetime(2026, 11, 9, 12), 3000.0),
            (datetime(2026, 11, 10, 12), 2700.0),
        ],
    )

    assert listings.get_by_id(saved.id).price == 2700.0


def test_listing_without_price_points_has_no_price(db, listings):
    saved = a_listing(db, "iPhone 13")

    assert listings.get_by_id(saved.id).price is None


def test_unknown_listing_is_none(listings):
    assert listings.get_by_id(999) is None


# cheapest_match


def test_cheapest_match_is_the_lowest_price_at_or_under_the_max(db, listings):
    a_listing(db, "iPhone 13 azul", prices=priced(2600.0))
    cheapest = a_listing(db, "iPhone 13 preto", prices=priced(2400.0))
    a_listing(db, "iPhone 13 rosa", prices=priced(3100.0))

    match = listings.cheapest_match("iphone 13", [OLX], max_price=2600.0)

    assert match.id == cheapest.id
    assert match.price == 2400.0


def test_cheapest_match_leaves_out_other_stores_and_unavailable_listings(db, listings):
    a_listing(db, "iPhone 13 Enjoei", store=ENJOEI, prices=priced(1000.0))
    a_listing(db, "iPhone 13 vendido", prices=priced(1100.0), available=False)
    expected = a_listing(db, "iPhone 13 OLX", prices=priced(2000.0))

    match = listings.cheapest_match("iPhone 13", [OLX], max_price=2600.0)

    assert match.id == expected.id


def test_cheapest_match_is_none_when_every_price_is_above_the_max(db, listings):
    a_listing(db, "iPhone 13", prices=priced(3100.0))

    assert listings.cheapest_match("iPhone 13", [OLX], max_price=2600.0) is None


# opportunities_for_alert


def test_opportunities_are_the_alerts_matches_at_or_under_its_max_price(db, listings):
    alert = a_keyword_alert(db, "iPhone 13", max_price=2600.0, stores=[OLX])
    at_max = a_listing(db, "iPhone 13 preto", prices=priced(2600.0))
    a_listing(db, "iPhone 13 caro", prices=priced(2601.0))
    a_listing(db, "iPhone 13 Enjoei", store=ENJOEI, prices=priced(1000.0))
    a_listing(db, "Galaxy S23", prices=priced(1000.0))

    found = listings.opportunities_for_alert(alert.id, limit=50)

    assert [listing.id for listing in found] == [at_max.id]


def test_opportunities_ignore_other_alerts(db, listings):
    alert = a_keyword_alert(db, "iPhone 13", max_price=2600.0, stores=[OLX])
    a_keyword_alert(db, "Galaxy", max_price=2600.0, stores=[OLX])
    a_listing(db, "Galaxy S23", prices=priced(1000.0))

    assert listings.opportunities_for_alert(alert.id, limit=50) == []


def test_opportunities_stop_at_the_limit(db, listings):
    alert = a_keyword_alert(db, "iPhone 13", max_price=2600.0, stores=[OLX])
    for color in ("azul", "preto", "rosa"):
        a_listing(db, f"iPhone 13 {color}", prices=priced(2000.0))

    assert len(listings.opportunities_for_alert(alert.id, limit=2)) == 2


# available_offers_for_book


def test_book_offers_are_that_books_offers_in_stock(db, listings):
    orwell = a_book(db, "9788535914849", "1984")
    other = a_book(db, "9788535902778", "A revolução dos bichos")
    used = a_listing(db, "1984 usado", prices=priced(20.0), book_id=orwell.id)
    new = a_listing(
        db, "1984 novo", prices=priced(55.0), condition="new", book_id=orwell.id
    )
    a_listing(
        db, "1984 esgotado", prices=priced(15.0), book_id=orwell.id, available=False
    )
    a_listing(db, "Bichos", prices=priced(10.0), book_id=other.id)

    found = listings.available_offers_for_book(orwell.id, limit=200)

    assert sorted((o.id, o.condition, o.price) for o in found) == sorted(
        [(used.id, "used", 20.0), (new.id, "new", 55.0)]
    )


def test_book_offers_stop_at_the_limit(db, listings):
    orwell = a_book(db, "9788535914849", "1984")
    for n in range(3):
        a_listing(db, f"1984 cópia {n}", prices=priced(20.0), book_id=orwell.id)

    assert len(listings.available_offers_for_book(orwell.id, limit=2)) == 2
