"""
Integration tests for SearchExecutionLogRepository.

Tests Repository + Database interactions with real SQLAlchemy operations.
Uses SQLite in-memory for fast, isolated tests.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.accounts.persistence.models import User  # noqa: F401

# Import all models to register with Base.metadata
from src.app.infrastructure.database.models.search_config_model import (  # noqa: F401
    SearchConfig as SearchConfigModel,
)
from src.app.infrastructure.database.models.search_config_source_website_model import (  # noqa: F401
    search_config_source_website,
)
from src.app.infrastructure.database.models.search_execution_log_model import (  # noqa: F401
    SearchExecutionLog as SearchExecutionLogModel,
)
from src.app.infrastructure.database_config import Base
from src.app.infrastructure.repositories.search_execution_log_repository import (
    SearchExecutionLogRepository,
)
from src.app.searches.entities import SearchRun
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
def search_execution_log_repository(test_db):
    return SearchExecutionLogRepository(test_db)


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
def sample_search_config(test_db, sample_user):
    """Creates a SearchConfig for FK references."""
    config = SearchConfigModel(
        search_term="laptop",
        is_active=True,
        frequency_days=1,
        user_id=sample_user.id,
    )
    test_db.add(config)
    test_db.commit()
    test_db.refresh(config)
    return config


@pytest.fixture
def sample_entity(sample_search_config):
    """Sample SearchExecutionLog entity (no id)."""
    return SearchRun(
        search_config_id=sample_search_config.id,
        status="pending",
    )


# ============================================================================
# Tests
# ============================================================================


class TestCreateSearchExecutionLog:
    def test_create_should_persist_and_return_entity_with_id(
        self, search_execution_log_repository, sample_entity
    ):
        result = search_execution_log_repository.create(sample_entity)

        assert result.id is not None
        assert result.search_config_id == sample_entity.search_config_id
        assert result.status == "pending"

    def test_create_two_records_should_assign_different_ids(
        self, search_execution_log_repository, sample_search_config
    ):
        r1 = search_execution_log_repository.create(
            SearchRun(search_config_id=sample_search_config.id, status="pending")
        )
        r2 = search_execution_log_repository.create(
            SearchRun(search_config_id=sample_search_config.id, status="success")
        )
        assert r1.id != r2.id

    def test_create_with_all_fields_should_persist_correctly(
        self, search_execution_log_repository, sample_search_config
    ):
        now = datetime.now(UTC).replace(microsecond=0)
        entity = SearchRun(
            search_config_id=sample_search_config.id,
            status="failed",
            results_count=0,
            error_message="Timeout error",
            started_at=now,
        )
        result = search_execution_log_repository.create(entity)

        assert result.status == "failed"
        assert result.results_count == 0
        assert result.error_message == "Timeout error"


class TestReadSearchExecutionLog:
    def test_get_by_id_with_existing_id_returns_entity(
        self, search_execution_log_repository, sample_entity
    ):
        created = search_execution_log_repository.create(sample_entity)
        result = search_execution_log_repository.get_by_id(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.search_config_id == sample_entity.search_config_id

    def test_get_by_id_with_nonexistent_id_returns_none(
        self, search_execution_log_repository
    ):
        assert search_execution_log_repository.get_by_id(99999) is None

    def test_get_by_search_config_id_returns_all_records(
        self, search_execution_log_repository, sample_search_config
    ):
        search_execution_log_repository.create(
            SearchRun(search_config_id=sample_search_config.id, status="pending")
        )
        search_execution_log_repository.create(
            SearchRun(search_config_id=sample_search_config.id, status="success")
        )

        results = search_execution_log_repository.get_by_search_config_id(
            sample_search_config.id
        )

        assert len(results) == 2

    def test_get_by_search_config_id_with_no_logs_returns_empty_list(
        self, search_execution_log_repository
    ):
        results = search_execution_log_repository.get_by_search_config_id(99999)
        assert results == []

    def test_get_all_returns_paginated_results(
        self, search_execution_log_repository, sample_search_config
    ):
        for _ in range(5):
            search_execution_log_repository.create(
                SearchRun(search_config_id=sample_search_config.id, status="success")
            )

        results, total = search_execution_log_repository.get_all(limit=3, offset=0)

        assert total == 5
        assert len(results) == 3

    def test_get_all_with_offset_returns_correct_page(
        self, search_execution_log_repository, sample_search_config
    ):
        for _ in range(5):
            search_execution_log_repository.create(
                SearchRun(search_config_id=sample_search_config.id, status="pending")
            )

        results, total = search_execution_log_repository.get_all(limit=3, offset=3)

        assert total == 5
        assert len(results) == 2

    def test_get_all_empty_returns_zero_total(self, search_execution_log_repository):
        results, total = search_execution_log_repository.get_all()

        assert results == []
        assert total == 0


class TestDeleteSearchExecutionLog:
    def test_delete_existing_record_returns_true(
        self, search_execution_log_repository, sample_entity
    ):
        created = search_execution_log_repository.create(sample_entity)
        result = search_execution_log_repository.delete(created.id)

        assert result is True
        assert search_execution_log_repository.get_by_id(created.id) is None

    def test_delete_nonexistent_record_returns_false(
        self, search_execution_log_repository
    ):
        result = search_execution_log_repository.delete(99999)
        assert result is False

    def test_delete_removes_only_target_record(
        self, search_execution_log_repository, sample_search_config
    ):
        r1 = search_execution_log_repository.create(
            SearchRun(search_config_id=sample_search_config.id, status="pending")
        )
        r2 = search_execution_log_repository.create(
            SearchRun(search_config_id=sample_search_config.id, status="success")
        )

        search_execution_log_repository.delete(r1.id)

        assert search_execution_log_repository.get_by_id(r1.id) is None
        assert search_execution_log_repository.get_by_id(r2.id) is not None
