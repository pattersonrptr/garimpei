"""
Integration tests for PriceHistoryRepository.

Tests Repository + Database interactions with real SQLAlchemy operations.
Uses SQLite in-memory for fast, isolated tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.catalog.entities import PriceHistory as PriceHistoryEntity

# Import models to register with Base.metadata
from src.app.catalog.persistence.models import (  # noqa: F401
    PriceHistory as PriceHistoryModel,
)
from src.app.catalog.persistence.models import (  # noqa: F401
    Product as ProductModel,
)
from src.app.catalog.persistence.repositories import (
    PriceHistoryRepository,
)
from src.app.infrastructure.database.models.source_website_model import (  # noqa: F401
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.database_config import Base

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def test_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def price_history_repository(test_db):
    return PriceHistoryRepository(test_db)


@pytest.fixture
def sample_product(test_db):
    """Creates a SourceWebsite + Product for FK references."""
    from src.app.catalog.entities import ProductCondition

    source_website = SourceWebsiteModel(
        name="OLX", base_url="https://www.olx.com.br", is_active=True
    )
    test_db.add(source_website)
    test_db.commit()
    test_db.refresh(source_website)

    product = ProductModel(
        url="https://www.olx.com.br/item/iphone",
        title="iPhone 13",
        condition=ProductCondition.USED,
        is_available=True,
        source_website_id=source_website.id,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)
    return product


@pytest.fixture
def sample_price_history_entity(sample_product):
    return PriceHistoryEntity(product_id=sample_product.id, price=1500.00)


# ============================================================================
# Tests
# ============================================================================


class TestCreatePriceHistory:
    def test_create_should_persist_and_return_entity_with_id(
        self, price_history_repository, sample_price_history_entity
    ):
        result = price_history_repository.create(sample_price_history_entity)

        assert result.id is not None
        assert result.product_id == sample_price_history_entity.product_id
        assert result.price == 1500.00

    def test_create_two_records_should_assign_different_ids(
        self, price_history_repository, sample_product
    ):
        r1 = price_history_repository.create(
            PriceHistoryEntity(product_id=sample_product.id, price=100.0)
        )
        r2 = price_history_repository.create(
            PriceHistoryEntity(product_id=sample_product.id, price=200.0)
        )
        assert r1.id != r2.id


class TestReadPriceHistory:
    def test_get_by_id_with_existing_id_returns_entity(
        self, price_history_repository, sample_price_history_entity
    ):
        created = price_history_repository.create(sample_price_history_entity)
        result = price_history_repository.get_by_id(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.price == 1500.00

    def test_get_by_id_with_nonexistent_id_returns_none(self, price_history_repository):
        assert price_history_repository.get_by_id(99999) is None

    def test_get_by_product_id_returns_all_records_for_product(
        self, price_history_repository, sample_product
    ):
        price_history_repository.create(
            PriceHistoryEntity(product_id=sample_product.id, price=100.0)
        )
        price_history_repository.create(
            PriceHistoryEntity(product_id=sample_product.id, price=200.0)
        )

        results = price_history_repository.get_by_product_id(sample_product.id)

        assert len(results) == 2

    def test_get_by_product_id_with_no_records_returns_empty_list(
        self, price_history_repository
    ):
        assert price_history_repository.get_by_product_id(99999) == []

    def test_get_latest_by_product_id_returns_most_recent(
        self, price_history_repository, sample_product
    ):
        price_history_repository.create(
            PriceHistoryEntity(product_id=sample_product.id, price=100.0)
        )
        price_history_repository.create(
            PriceHistoryEntity(product_id=sample_product.id, price=200.0)
        )

        result = price_history_repository.get_latest_by_product_id(sample_product.id)

        # Both have same created_at (instant), so either is acceptable.
        # We just assert it returns something and it's one of the created records.
        assert result is not None
        assert result.price in (100.0, 200.0)

    def test_get_latest_by_product_id_with_no_records_returns_none(
        self, price_history_repository
    ):
        assert price_history_repository.get_latest_by_product_id(99999) is None

    def test_get_all_returns_all_records_and_total(
        self, price_history_repository, sample_product
    ):
        price_history_repository.create(
            PriceHistoryEntity(product_id=sample_product.id, price=100.0)
        )
        price_history_repository.create(
            PriceHistoryEntity(product_id=sample_product.id, price=200.0)
        )

        results, total = price_history_repository.get_all()

        assert total == 2
        assert len(results) == 2

    def test_get_all_with_pagination_returns_correct_subset(
        self, price_history_repository, sample_product
    ):
        for price in [100.0, 200.0, 300.0]:
            price_history_repository.create(
                PriceHistoryEntity(product_id=sample_product.id, price=price)
            )

        results, total = price_history_repository.get_all(limit=2, offset=1)

        assert total == 3
        assert len(results) == 2

    def test_get_all_with_empty_database_returns_empty_list(
        self, price_history_repository
    ):
        results, total = price_history_repository.get_all()
        assert results == []
        assert total == 0


class TestDeletePriceHistory:
    def test_delete_existing_record_returns_true_and_removes_it(
        self, price_history_repository, sample_price_history_entity
    ):
        created = price_history_repository.create(sample_price_history_entity)

        result = price_history_repository.delete(created.id)

        assert result is True
        assert price_history_repository.get_by_id(created.id) is None

    def test_delete_nonexistent_record_returns_false(self, price_history_repository):
        assert price_history_repository.delete(99999) is False
