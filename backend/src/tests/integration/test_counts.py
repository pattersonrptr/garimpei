"""Each module counts its own records (admin module plan, slice 1).

The admin summary asks accounts, alerts, catalog and stores how many records
they hold. The rules (what counts as active, soft-deleted alerts left out)
live in each repository's query, so these tests run the use cases over the
real repositories on SQLite.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.accounts.persistence.models import User as UserModel
from src.app.accounts.persistence.repositories import UserRepository
from src.app.accounts.use_cases import CountUsersUseCase
from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.alerts.persistence.repositories import PriceAlertRepository
from src.app.alerts.use_cases import CountPriceAlertsUseCase
from src.app.catalog.entities import ProductCondition
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.catalog.persistence.repositories import ProductRepository
from src.app.catalog.use_cases import CountProductsUseCase
from src.app.infrastructure.database import models  # noqa: F401
from src.app.infrastructure.database_config import Base
from src.app.stores.persistence.models import Store as StoreModel
from src.app.stores.persistence.repositories import StoreRepository
from src.app.stores.use_cases import CountStoresUseCase


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def add(db, *rows):
    db.add_all(rows)
    db.commit()
    return rows


def user(name, is_active=True):
    return UserModel(
        username=name,
        email=f"{name}@example.com",
        hashed_password="x",
        is_active=is_active,
    )


def store(name, is_active=True):
    return StoreModel(
        name=name, base_url=f"https://{name}.example.com", is_active=is_active
    )


def alert(owner, term, is_active=True, deleted_at=None):
    return PriceAlertModel(
        search_term=term,
        max_price=100.0,
        is_active=is_active,
        frequency_minutes=60,
        user_id=owner.id,
        deleted_at=deleted_at,
    )


class TestCountUsers:
    def test_counts_every_user(self, db):
        add(db, user("ana"), user("bia", is_active=False))

        assert CountUsersUseCase(UserRepository(db)).execute() == 2

    def test_counts_only_active_users_when_asked(self, db):
        add(db, user("ana"), user("bia", is_active=False))

        assert CountUsersUseCase(UserRepository(db)).execute(active_only=True) == 1


class TestCountPriceAlerts:
    @pytest.fixture
    def alerts(self, db):
        [owner] = add(db, user("ana"))
        add(
            db,
            alert(owner, "active"),
            alert(owner, "paused", is_active=False),
            alert(owner, "deleted", deleted_at=datetime.now(UTC)),
            alert(
                owner, "deleted paused", is_active=False, deleted_at=datetime.now(UTC)
            ),
        )
        return CountPriceAlertsUseCase(PriceAlertRepository(db))

    def test_counts_alerts_leaving_out_soft_deleted_ones(self, alerts):
        assert alerts.execute() == 2

    def test_counts_only_active_alerts_when_asked(self, alerts):
        assert alerts.execute(active_only=True) == 1


class TestCountProducts:
    def test_counts_every_product_available_or_not(self, db):
        [shop] = add(db, store("shop"))
        add(
            db,
            *[
                ProductModel(
                    url=f"https://shop.example.com/{title}",
                    title=title,
                    condition=ProductCondition.NEW,
                    is_available=available,
                    source_website_id=shop.id,
                )
                for title, available in (("in-stock", True), ("sold-out", False))
            ],
        )

        assert CountProductsUseCase(ProductRepository(db)).execute() == 2


class TestCountStores:
    def test_counts_every_store(self, db):
        add(db, store("open"), store("closed", is_active=False))

        assert CountStoresUseCase(StoreRepository(db)).execute() == 2

    def test_counts_only_active_stores_when_asked(self, db):
        add(db, store("open"), store("closed", is_active=False))

        assert CountStoresUseCase(StoreRepository(db)).execute(active_only=True) == 1
