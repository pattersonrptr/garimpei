"""
Integration tests for StoreRepository.

Tests Repository + Database interactions with real SQLAlchemy operations.
Uses SQLite in-memory for fast, isolated tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.catalog.persistence.models import Product as ProductModel
from src.app.infrastructure.database_config import Base
from src.app.stores.entities import Store

# Import model to register with Base.metadata
from src.app.stores.persistence.models import Store as StoreModel  # noqa: F401
from src.app.stores.persistence.repositories import StoreRepository
from src.app.stores.use_cases import StoreHasOffersError

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
def source_website_repository(test_db):
    """StoreRepository with test database session."""
    return StoreRepository(test_db)


@pytest.fixture
def sample_store_entity():
    """Sample source website entity for testing (no id)."""
    return Store(
        name="OLX",
        base_url="https://www.olx.com.br",
        is_active=True,
    )


# ============================================================================
# Tests
# ============================================================================


class TestCreateSourceWebsite:
    """Tests for StoreRepository.create"""

    def test_create_should_persist_and_return_entity_with_id(
        self, source_website_repository, sample_store_entity
    ):
        """
        Given: A valid source website entity
        When: create is called
        Then: Entity is persisted and returned with an assigned ID
        """
        result = source_website_repository.create(sample_store_entity)

        assert result.id is not None
        assert result.name == "OLX"
        assert result.base_url == "https://www.olx.com.br"
        assert result.is_active is True

    def test_create_two_source_websites_should_assign_different_ids(
        self, source_website_repository
    ):
        """
        Given: Two different source website entities
        When: both are created
        Then: They receive distinct IDs
        """
        sw1 = Store(name="OLX", base_url="https://www.olx.com.br")
        sw2 = Store(name="Enjoei", base_url="https://www.enjoei.com.br")

        result1 = source_website_repository.create(sw1)
        result2 = source_website_repository.create(sw2)

        assert result1.id != result2.id


class TestReadSourceWebsite:
    """Tests for StoreRepository read operations"""

    def test_get_by_id_with_existing_id_should_return_entity(
        self, source_website_repository, sample_store_entity
    ):
        """
        Given: A source website is created in the database
        When: get_by_id is called with its ID
        Then: Returns the corresponding entity
        """
        created = source_website_repository.create(sample_store_entity)

        result = source_website_repository.get_by_id(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.name == "OLX"

    def test_get_by_id_with_nonexistent_id_should_return_none(
        self, source_website_repository
    ):
        """
        Given: No source website with the given ID exists
        When: get_by_id is called
        Then: Returns None
        """
        result = source_website_repository.get_by_id(99999)

        assert result is None

    def test_get_by_name_with_existing_name_should_return_entity(
        self, source_website_repository, sample_store_entity
    ):
        """
        Given: A source website with the given name exists
        When: get_by_name is called
        Then: Returns the corresponding entity
        """
        source_website_repository.create(sample_store_entity)

        result = source_website_repository.get_by_name("OLX")

        assert result is not None
        assert result.name == "OLX"

    def test_get_by_name_with_nonexistent_name_should_return_none(
        self, source_website_repository
    ):
        """
        Given: No source website with the given name exists
        When: get_by_name is called
        Then: Returns None
        """
        result = source_website_repository.get_by_name("DoesNotExist")

        assert result is None

    def test_get_all_should_return_all_entities_and_total(
        self, source_website_repository
    ):
        """
        Given: Two source websites in the database
        When: get_all is called
        Then: Returns list of 2 entities and total=2
        """
        source_website_repository.create(
            Store(name="OLX", base_url="https://www.olx.com.br")
        )
        source_website_repository.create(
            Store(name="Enjoei", base_url="https://www.enjoei.com.br")
        )

        results, total = source_website_repository.get_all()

        assert total == 2
        assert len(results) == 2

    def test_get_all_with_pagination_should_return_correct_subset(
        self, source_website_repository
    ):
        """
        Given: Three source websites in the database
        When: get_all is called with limit=2 and offset=1
        Then: Returns 2 entities starting from offset 1, total=3
        """
        for name, url in [
            ("OLX", "https://www.olx.com.br"),
            ("Enjoei", "https://www.enjoei.com.br"),
            ("Mercado Livre", "https://www.mercadolivre.com.br"),
        ]:
            source_website_repository.create(Store(name=name, base_url=url))

        results, total = source_website_repository.get_all(limit=2, offset=1)

        assert total == 3
        assert len(results) == 2

    def test_get_all_with_empty_database_should_return_empty_list(
        self, source_website_repository
    ):
        """
        Given: No source websites in the database
        When: get_all is called
        Then: Returns empty list and total=0
        """
        results, total = source_website_repository.get_all()

        assert results == []
        assert total == 0


class TestUpdateSourceWebsite:
    """Tests for StoreRepository.update"""

    def test_update_with_existing_entity_should_return_updated_entity(
        self, source_website_repository, sample_store_entity
    ):
        """
        Given: A source website exists in the database
        When: update is called with changed fields
        Then: Returns the updated entity
        """
        created = source_website_repository.create(sample_store_entity)

        update_entity = Store(
            id=created.id,
            name="OLX Brasil",
            base_url="https://www.olx.com.br",
            is_active=True,
        )
        result = source_website_repository.update(created.id, update_entity)

        assert result is not None
        assert result.name == "OLX Brasil"
        assert result.id == created.id

    def test_update_with_nonexistent_entity_should_return_none(
        self, source_website_repository, sample_store_entity
    ):
        """
        Given: No source website with the given ID exists
        When: update is called
        Then: Returns None
        """
        result = source_website_repository.update(99999, sample_store_entity)

        assert result is None


class TestDeleteSourceWebsite:
    """Tests for StoreRepository.delete"""

    def test_delete_with_existing_entity_should_return_true_and_remove_it(
        self, source_website_repository, sample_store_entity
    ):
        """
        Given: A source website exists in the database
        When: delete is called with its ID
        Then: Returns True and entity is no longer retrievable
        """
        created = source_website_repository.create(sample_store_entity)

        result = source_website_repository.delete(created.id)

        assert result is True
        assert source_website_repository.get_by_id(created.id) is None

    def test_delete_with_nonexistent_entity_should_return_false(
        self, source_website_repository
    ):
        """
        Given: No source website with the given ID exists
        When: delete is called
        Then: Returns False
        """
        result = source_website_repository.delete(99999)

        assert result is False

    def test_deleting_a_store_with_an_offer_is_refused_and_keeps_the_store(
        self, test_db, source_website_repository, sample_store_entity
    ):
        """A store that has offers is kept (rule decided Nov 27, 2026, #251)."""
        created = source_website_repository.create(sample_store_entity)
        test_db.add(
            ProductModel(
                url="https://www.olx.com.br/item/1",
                title="Duna",
                source_website_id=created.id,
            )
        )
        test_db.commit()

        with pytest.raises(StoreHasOffersError):
            source_website_repository.delete(created.id)

        assert source_website_repository.get_by_id(created.id) is not None
