"""Catalog deletes stale products no active alert finds (admin plan, slice 3).

`DeleteStaleProductsUseCase` runs over catalog's real repository with the
ListingScope alerts implements, on SQLite, since the rule (which alerts keep
a product) lives in the query.
"""

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.accounts.persistence.models import User as UserModel
from src.app.alerts.persistence.listing_scope import AlertListingScope
from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.alerts.persistence.models import price_alert_source_website
from src.app.catalog.entities import ProductCondition, StaleProductsCleanup
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.catalog.persistence.repositories import ProductRepository
from src.app.catalog.use_cases import DeleteStaleProductsUseCase
from src.app.infrastructure.database import models  # noqa: F401
from src.app.infrastructure.database_config import Base
from src.app.stores.persistence.models import Store as StoreModel

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=UTC)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(StoreModel(id=1, name="Sebo", base_url="https://sebo.example.com"))
    session.add(UserModel(id=1, username="ana", email="ana@x.com", hashed_password="x"))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def cleanup(db) -> DeleteStaleProductsUseCase:
    return DeleteStaleProductsUseCase(
        ProductRepository(db, AlertListingScope()), now=lambda: NOW
    )


def a_product(db, title: str, days_old: int) -> int:
    product = ProductModel(
        url=f"https://sebo.example.com/{title.lower().replace(' ', '-')}",
        title=title,
        condition=ProductCondition.USED,
        is_available=True,
        source_website_id=1,
        updated_at=NOW - timedelta(days=days_old),
    )
    db.add(product)
    db.commit()
    return cast(int, product.id)


def an_alert(db, term: str, is_active: bool = True) -> None:
    alert = PriceAlertModel(
        search_term=term,
        max_price=10.0,
        is_active=is_active,
        frequency_minutes=60,
        user_id=1,
    )
    db.add(alert)
    db.commit()
    db.execute(
        price_alert_source_website.insert().values(
            price_alert_id=alert.id, source_website_id=1
        )
    )
    db.commit()


def exists(db, product_id: int) -> bool:
    db.expire_all()
    return db.get(ProductModel, product_id) is not None


def test_deletes_products_not_updated_within_days_old(db):
    stale = a_product(db, "Old Atlas", days_old=31)
    fresh = a_product(db, "New Atlas", days_old=29)

    result = cleanup(db).execute(days_old=30, dry_run=False)

    assert result == StaleProductsCleanup(eligible=1, deleted=1)
    assert not exists(db, stale)
    assert exists(db, fresh)


def test_a_dry_run_counts_without_deleting(db):
    stale = a_product(db, "Old Atlas", days_old=31)

    result = cleanup(db).execute(days_old=30, dry_run=True)

    assert result == StaleProductsCleanup(eligible=1, deleted=0)
    assert exists(db, stale)


def test_keeps_a_stale_product_an_active_alert_finds(db):
    an_alert(db, "atlas")
    found = a_product(db, "Old Atlas", days_old=31)

    result = cleanup(db).execute(days_old=30, dry_run=False)

    assert result == StaleProductsCleanup(eligible=0, deleted=0)
    assert exists(db, found)


def test_a_paused_alert_does_not_keep_a_stale_product(db):
    an_alert(db, "atlas", is_active=False)
    stale = a_product(db, "Old Atlas", days_old=31)

    result = cleanup(db).execute(days_old=30, dry_run=False)

    assert result == StaleProductsCleanup(eligible=1, deleted=1)
    assert not exists(db, stale)
