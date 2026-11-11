"""
Integration tests for ProductRepository.

Tests Repository + Database interactions with real SQLAlchemy operations.
Uses SQLite in-memory for fast, isolated tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.entities import ProductCondition
from src.app.catalog.persistence.repositories import ProductRepository

# Import models to register with Base.metadata
from src.app.infrastructure.database.models import (  # noqa: F401
    Product as ProductModel,
)
from src.app.infrastructure.database.models import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.database_config import Base

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def test_db():
    """
    Creates an in-memory SQLite database for each test.
    Ensures complete isolation between tests.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def product_repository(test_db):
    """ProductRepository with test database session."""
    return ProductRepository(test_db)


@pytest.fixture
def sample_source_website(test_db):
    """Creates a SourceWebsite in the database for foreign key references."""
    source_website = SourceWebsiteModel(
        name="OLX",
        base_url="https://www.olx.com.br",
        is_active=True,
    )
    test_db.add(source_website)
    test_db.commit()
    test_db.refresh(source_website)
    return source_website


@pytest.fixture
def sample_product_entity(sample_source_website):
    """Sample product entity for testing."""
    return ProductEntity(
        url="https://www.olx.com.br/item/iphone-13",
        title="iPhone 13 128GB",
        source_product_code="OLX-001",
        description="iPhone em ótimo estado",
        condition=ProductCondition.USED,
        seller_name="João Silva",
        is_available=True,
        source_website_id=sample_source_website.id,
    )


# ============================================================================
# Create Tests
# ============================================================================


class TestProductRepositoryCreate:
    """Tests for ProductRepository.create()."""

    def test_create_product_should_persist_to_database(
        self, product_repository, sample_product_entity
    ):
        """
        Given: Valid product entity
        When: repository.create() is called
        Then: Should persist product to database with generated ID and timestamps
        """
        # When
        created_product = product_repository.create(sample_product_entity)

        # Then
        assert created_product.id is not None
        assert created_product.url == "https://www.olx.com.br/item/iphone-13"
        assert created_product.title == "iPhone 13 128GB"
        assert created_product.condition == ProductCondition.USED
        assert created_product.created_at is not None
        assert created_product.updated_at is not None

        # Verify: Fetch from database
        found = product_repository.get_by_id(created_product.id)
        assert found is not None
        assert found.url == created_product.url

    def test_create_product_should_use_default_values(
        self, product_repository, sample_source_website
    ):
        """
        Given: Product entity with only required fields
        When: repository.create() is called
        Then: Should use default values for optional fields
        """
        # Given
        minimal_product = ProductEntity(
            url="https://www.olx.com.br/item/minimal",
            title="Minimal Product",
            source_website_id=sample_source_website.id,
        )

        # When
        created = product_repository.create(minimal_product)

        # Then
        assert created.is_available is True
        assert created.condition == ProductCondition.UNDETERMINED


# ============================================================================
# Read Tests
# ============================================================================


class TestProductRepositoryRead:
    """Tests for ProductRepository read operations."""

    def test_get_by_id_should_return_product(
        self, product_repository, sample_product_entity
    ):
        """
        Given: Product exists in database
        When: repository.get_by_id() is called
        Then: Should return correct product entity
        """
        # Given
        created = product_repository.create(sample_product_entity)

        # When
        found = product_repository.get_by_id(created.id)

        # Then
        assert found is not None
        assert found.id == created.id
        assert found.title == "iPhone 13 128GB"
        assert found.url == "https://www.olx.com.br/item/iphone-13"

    def test_get_by_id_nonexistent_should_return_none(self, product_repository):
        """
        Given: Product ID does not exist
        When: repository.get_by_id() is called
        Then: Should return None
        """
        assert product_repository.get_by_id(999) is None

    def test_get_by_url_should_return_product(
        self, product_repository, sample_product_entity
    ):
        """
        Given: Product exists in database
        When: repository.get_by_url() is called with the product's URL
        Then: Should return correct product entity
        """
        # Given
        product_repository.create(sample_product_entity)

        # When
        found = product_repository.get_by_url("https://www.olx.com.br/item/iphone-13")

        # Then
        assert found is not None
        assert found.title == "iPhone 13 128GB"

    def test_get_by_url_nonexistent_should_return_none(self, product_repository):
        """
        Given: URL does not match any product
        When: repository.get_by_url() is called
        Then: Should return None
        """
        assert (
            product_repository.get_by_url("https://www.olx.com.br/item/ghost") is None
        )

    def test_get_all_should_return_products_and_total(
        self, product_repository, sample_source_website
    ):
        """
        Given: Multiple products in database
        When: repository.get_all() is called
        Then: Should return list of products and total count
        """
        # Given
        for i in range(3):
            product_repository.create(
                ProductEntity(
                    url=f"https://www.olx.com.br/item/product-{i}",
                    title=f"Product {i}",
                    source_website_id=sample_source_website.id,
                )
            )

        # When
        products, total = product_repository.get_all()

        # Then
        assert total == 3
        assert len(products) == 3

    def test_get_all_with_pagination_should_return_correct_slice(
        self, product_repository, sample_source_website
    ):
        """
        Given: 5 products in database
        When: repository.get_all() is called with limit=2, offset=2
        Then: Should return 2 products starting from index 2 and total=5
        """
        # Given
        for i in range(5):
            product_repository.create(
                ProductEntity(
                    url=f"https://www.olx.com.br/item/product-{i}",
                    title=f"Product {i}",
                    source_website_id=sample_source_website.id,
                )
            )

        # When
        products, total = product_repository.get_all(limit=2, offset=2)

        # Then
        assert total == 5
        assert len(products) == 2

    def test_get_all_empty_database_should_return_empty_list(self, product_repository):
        """
        Given: No products in database
        When: repository.get_all() is called
        Then: Should return empty list and total=0
        """
        products, total = product_repository.get_all()
        assert products == []
        assert total == 0


# ============================================================================
# Update Tests
# ============================================================================


class TestProductRepositoryUpdate:
    """Tests for ProductRepository.update()."""

    def test_update_product_should_persist_changes(
        self, product_repository, sample_product_entity
    ):
        """
        Given: Existing product in database
        When: repository.update() is called with modified data
        Then: Should persist changes and update updated_at
        """
        # Given
        created = product_repository.create(sample_product_entity)
        original_updated_at = created.updated_at

        # When
        created.title = "iPhone 13 128GB - Updated"
        created.is_available = False
        updated = product_repository.update(created.id, created)

        # Then
        assert updated is not None
        assert updated.title == "iPhone 13 128GB - Updated"
        assert updated.is_available is False
        assert updated.updated_at >= original_updated_at

        # Verify from database
        found = product_repository.get_by_id(created.id)
        assert found.title == "iPhone 13 128GB - Updated"

    def test_update_nonexistent_product_should_return_none(
        self, product_repository, sample_product_entity
    ):
        """
        Given: Product ID does not exist
        When: repository.update() is called
        Then: Should return None
        """
        result = product_repository.update(999, sample_product_entity)
        assert result is None


# ============================================================================
# Delete Tests
# ============================================================================


class TestProductRepositoryDelete:
    """Tests for ProductRepository.delete()."""

    def test_delete_product_should_remove_from_database(
        self, product_repository, sample_product_entity
    ):
        """
        Given: Product exists in database
        When: repository.delete() is called
        Then: Should remove product and return True
        """
        # Given
        created = product_repository.create(sample_product_entity)

        # When
        result = product_repository.delete(created.id)

        # Then
        assert result is True
        assert product_repository.get_by_id(created.id) is None

    def test_delete_nonexistent_product_should_return_false(self, product_repository):
        """
        Given: Product ID does not exist
        When: repository.delete() is called
        Then: Should return False
        """
        assert product_repository.delete(999) is False


# ============================================================================
# Freshness: the latest price point says when the offer was last checked
# ============================================================================


class TestProductRepositoryFreshness:
    @pytest.fixture
    def offer_with_points(self, test_db, product_repository, sample_product_entity):
        from datetime import datetime

        from src.app.catalog.persistence.models import (
            PriceHistory as PriceHistoryModel,
        )

        offer = product_repository.create(sample_product_entity)
        test_db.add_all(
            [
                PriceHistoryModel(
                    product_id=offer.id, price=30, created_at=datetime(2026, 11, 9, 3)
                ),
                PriceHistoryModel(
                    product_id=offer.id, price=28, created_at=datetime(2026, 11, 10, 3)
                ),
            ]
        )
        test_db.commit()
        return offer

    def assert_latest_point(self, product):
        from datetime import UTC, datetime

        assert product.current_price == 28
        assert product.last_checked_at == datetime(2026, 11, 10, 3, tzinfo=UTC)

    def test_get_by_id_and_url_carry_the_last_check_in_utc(
        self, product_repository, offer_with_points
    ):
        self.assert_latest_point(product_repository.get_by_id(offer_with_points.id))
        self.assert_latest_point(product_repository.get_by_url(offer_with_points.url))

    def test_get_all_carries_the_last_check(
        self, product_repository, offer_with_points
    ):
        (product,), _ = product_repository.get_all()

        self.assert_latest_point(product)

    def test_search_carries_the_last_check(
        self, product_repository, offer_with_points, sample_source_website
    ):
        (product,), _ = product_repository.search_by_term_and_sources(
            "iPhone", [sample_source_website.id]
        )

        self.assert_latest_point(product)

    def test_an_offer_never_priced_has_no_last_check(
        self, product_repository, sample_product_entity
    ):
        offer = product_repository.create(sample_product_entity)

        assert product_repository.get_by_id(offer.id).last_checked_at is None
