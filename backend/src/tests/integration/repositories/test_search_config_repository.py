"""
Integration tests for SavedSearchRepository.

Tests Repository + Database interactions with real SQLAlchemy operations.
Uses SQLite in-memory for fast, isolated tests.
"""

from datetime import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.accounts.persistence.models import User  # noqa: F401
from src.app.infrastructure.database_config import Base
from src.app.searches.entities import SavedSearch

# Import all models to register with Base.metadata
from src.app.searches.persistence.models import SavedSearch as SavedSearchModel  # noqa: F401
from src.app.searches.persistence.models import (  # noqa: F401
    search_config_source_website,
)
from src.app.searches.persistence.repositories import SavedSearchRepository
from src.app.stores.persistence.models import Store as StoreModel  # noqa: F401

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def test_db():
    """Creates an in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def search_config_repository(test_db):
    return SavedSearchRepository(test_db)


@pytest.fixture
def sample_user(test_db):
    """Creates a User for FK references."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_store(test_db):
    """Creates a SourceWebsite for M2M references."""
    sw = StoreModel(
        name="OLX",
        base_url="https://www.olx.com.br",
        is_active=True,
    )
    test_db.add(sw)
    test_db.commit()
    test_db.refresh(sw)
    return sw


@pytest.fixture
def sample_entity(sample_user):
    """Sample SearchConfig entity (no id, no source websites)."""
    return SavedSearch(
        search_term="iPhone 13",
        is_active=True,
        frequency_days=1,
        preferred_time=time(8, 0),
        user_id=sample_user.id,
        source_website_ids=[],
    )


# ============================================================================
# Tests
# ============================================================================


class TestCreateSearchConfig:
    """Tests for SavedSearchRepository.create"""

    def test_create_persists_and_returns_entity_with_id(
        self, search_config_repository, sample_entity
    ):
        """
        Given: A valid search config entity
        When: create is called
        Then: Entity is persisted and returned with an assigned ID
        """
        result = search_config_repository.create(sample_entity)

        assert result.id is not None
        assert result.search_term == "iPhone 13"
        assert result.is_active is True
        assert result.frequency_days == 1
        assert result.source_website_ids == []

    def test_create_with_source_websites_persists_m2m(
        self, search_config_repository, sample_user, sample_store
    ):
        """
        Given: A search config entity with source_website_ids
        When: create is called
        Then: M2M relationship is persisted and ids are returned
        """
        entity = SavedSearch(
            search_term="Laptop",
            user_id=sample_user.id,
            source_website_ids=[sample_store.id],
        )
        result = search_config_repository.create(entity)

        assert result.id is not None
        assert result.source_website_ids == [sample_store.id]

    def test_create_two_configs_assigns_different_ids(
        self, search_config_repository, sample_user
    ):
        """
        Given: Two distinct search config entities
        When: both are created
        Then: They receive distinct IDs
        """
        e1 = SavedSearch(search_term="iPhone", user_id=sample_user.id)
        e2 = SavedSearch(search_term="Samsung", user_id=sample_user.id)

        r1 = search_config_repository.create(e1)
        r2 = search_config_repository.create(e2)

        assert r1.id != r2.id


class TestGetSearchConfigById:
    """Tests for SavedSearchRepository.get_by_id"""

    def test_get_by_id_returns_entity_when_found(
        self, search_config_repository, sample_entity
    ):
        """
        Given: A persisted search config
        When: get_by_id is called with its id
        Then: Returns the entity
        """
        created = search_config_repository.create(sample_entity)
        result = search_config_repository.get_by_id(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.search_term == "iPhone 13"

    def test_get_by_id_returns_none_when_not_found(self, search_config_repository):
        """
        Given: A non-existent id
        When: get_by_id is called
        Then: Returns None
        """
        result = search_config_repository.get_by_id(99999)

        assert result is None


class TestGetSearchConfigsByUserId:
    """Tests for SavedSearchRepository.get_by_user_id"""

    def test_get_by_user_id_returns_all_configs_for_user(
        self, search_config_repository, sample_user
    ):
        """
        Given: Two search configs for the same user
        When: get_by_user_id is called
        Then: Returns both entities
        """
        e1 = SavedSearch(search_term="iPhone", user_id=sample_user.id)
        e2 = SavedSearch(search_term="iPad", user_id=sample_user.id)
        search_config_repository.create(e1)
        search_config_repository.create(e2)

        results = search_config_repository.get_by_user_id(sample_user.id)

        assert len(results) == 2
        terms = {r.search_term for r in results}
        assert terms == {"iPhone", "iPad"}

    def test_get_by_user_id_returns_empty_for_unknown_user(
        self, search_config_repository
    ):
        """
        Given: A user_id with no configs
        When: get_by_user_id is called
        Then: Returns empty list
        """
        results = search_config_repository.get_by_user_id(99999)

        assert results == []


class TestGetSearchConfigByTermAndUserId:
    """Tests for SavedSearchRepository.get_by_search_term_and_user_id"""

    def test_returns_entity_when_found(self, search_config_repository, sample_user):
        """
        Given: A persisted config with a specific term and user
        When: get_by_search_term_and_user_id is called
        Then: Returns the entity
        """
        search_config_repository.create(
            SavedSearch(search_term="Xbox", user_id=sample_user.id)
        )
        result = search_config_repository.get_by_search_term_and_user_id(
            "Xbox", sample_user.id
        )

        assert result is not None
        assert result.search_term == "Xbox"

    def test_returns_none_when_term_not_found_for_user(
        self, search_config_repository, sample_user
    ):
        """
        Given: Term that doesn't exist for this user
        When: get_by_search_term_and_user_id is called
        Then: Returns None
        """
        result = search_config_repository.get_by_search_term_and_user_id(
            "PlayStation", sample_user.id
        )

        assert result is None


class TestGetAllSearchConfigs:
    """Tests for SavedSearchRepository.get_all"""

    def test_get_all_returns_all_configs_and_total(
        self, search_config_repository, sample_user
    ):
        """
        Given: Two persisted search configs
        When: get_all is called
        Then: Returns (list, total=2)
        """
        search_config_repository.create(
            SavedSearch(search_term="iPhone", user_id=sample_user.id)
        )
        search_config_repository.create(
            SavedSearch(search_term="Android", user_id=sample_user.id)
        )

        results, total = search_config_repository.get_all(limit=10, offset=0)

        assert total == 2
        assert len(results) == 2

    def test_get_all_respects_limit(self, search_config_repository, sample_user):
        """
        Given: Three persisted search configs
        When: get_all is called with limit=2
        Then: Returns only 2 items but total=3
        """
        for term in ["iPhone", "Android", "Windows"]:
            search_config_repository.create(
                SavedSearch(search_term=term, user_id=sample_user.id)
            )

        results, total = search_config_repository.get_all(limit=2, offset=0)

        assert total == 3
        assert len(results) == 2


class TestUpdateSearchConfig:
    """Tests for SavedSearchRepository.update"""

    def test_update_changes_fields(self, search_config_repository, sample_entity):
        """
        Given: A persisted search config
        When: update is called with new values
        Then: The record is updated and returned
        """
        created = search_config_repository.create(sample_entity)

        updated_entity = SavedSearch(
            id=created.id,
            search_term="iPhone 14 Pro",
            is_active=False,
            frequency_days=7,
            preferred_time=time(10, 0),
            user_id=created.user_id,
            source_website_ids=[],
        )
        result = search_config_repository.update(created.id, updated_entity)

        assert result is not None
        assert result.search_term == "iPhone 14 Pro"
        assert result.is_active is False
        assert result.frequency_days == 7

    def test_update_returns_none_when_not_found(
        self, search_config_repository, sample_entity
    ):
        """
        Given: Non-existent id
        When: update is called
        Then: Returns None
        """
        result = search_config_repository.update(99999, sample_entity)

        assert result is None

    def test_update_syncs_source_websites(
        self, search_config_repository, sample_user, sample_store
    ):
        """
        Given: A search config without source websites
        When: update is called with source_website_ids
        Then: M2M relationship is updated
        """
        created = search_config_repository.create(
            SavedSearch(search_term="Laptop", user_id=sample_user.id)
        )

        updated_entity = SavedSearch(
            id=created.id,
            search_term="Laptop",
            is_active=True,
            frequency_days=1,
            preferred_time=time(0, 0),
            user_id=sample_user.id,
            source_website_ids=[sample_store.id],
        )
        result = search_config_repository.update(created.id, updated_entity)

        assert result.source_website_ids == [sample_store.id]


class TestDeleteSearchConfig:
    """Tests for SavedSearchRepository.delete"""

    def test_delete_removes_record_and_returns_true(
        self, search_config_repository, sample_entity
    ):
        """
        Given: A persisted search config
        When: delete is called
        Then: Returns True and record is gone
        """
        created = search_config_repository.create(sample_entity)
        result = search_config_repository.delete(created.id)

        assert result is True
        assert search_config_repository.get_by_id(created.id) is None

    def test_delete_returns_false_when_not_found(self, search_config_repository):
        """
        Given: A non-existent id
        When: delete is called
        Then: Returns False
        """
        result = search_config_repository.delete(99999)

        assert result is False
