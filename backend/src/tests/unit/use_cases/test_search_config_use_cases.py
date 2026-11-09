"""Unit tests for SearchConfig Use Cases."""

from datetime import datetime, time
from unittest.mock import Mock

import pytest

from src.app.entities.search_config import SearchConfig as SearchConfigEntity
from src.app.use_cases.search_config_use_cases import (
    CreateSearchConfigUseCase,
    DeleteSearchConfigUseCase,
    GetSearchConfigByIdUseCase,
    GetSearchConfigsByUserIdUseCase,
    ListSearchConfigsUseCase,
    UpdateSearchConfigUseCase,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_repo():
    return Mock()


@pytest.fixture
def sample_entity():
    return SearchConfigEntity(
        id=1,
        search_term="iPhone 13",
        is_active=True,
        frequency_days=1,
        preferred_time=time(8, 0),
        user_id=1,
        source_website_ids=[],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def new_entity():
    """Entity without id (before persistence)."""
    return SearchConfigEntity(
        search_term="Samsung S23",
        is_active=True,
        frequency_days=2,
        preferred_time=time(9, 0),
        user_id=2,
        source_website_ids=[],
    )


# ============================================================================
# Tests
# ============================================================================


class TestCreateSearchConfigUseCase:
    """Tests for CreateSearchConfigUseCase.execute"""

    def test_execute_calls_repo_and_returns_entity(
        self, mock_repo, new_entity, sample_entity
    ):
        """
        Given: A new entity and a mock repository
        When: execute is called
        Then: Repository.create is called and result returned
        """
        mock_repo.create.return_value = sample_entity

        use_case = CreateSearchConfigUseCase(mock_repo)
        result = use_case.execute(new_entity)

        mock_repo.create.assert_called_once_with(new_entity)
        assert result == sample_entity


class TestGetSearchConfigByIdUseCase:
    """Tests for GetSearchConfigByIdUseCase.execute"""

    def test_execute_returns_entity_when_found(self, mock_repo, sample_entity):
        """
        Given: Existing search config id
        When: execute is called
        Then: Returns entity
        """
        mock_repo.get_by_id.return_value = sample_entity

        result = GetSearchConfigByIdUseCase(mock_repo).execute(1)

        mock_repo.get_by_id.assert_called_once_with(1)
        assert result == sample_entity

    def test_execute_returns_none_when_not_found(self, mock_repo):
        """
        Given: Non-existent id
        When: execute is called
        Then: Returns None
        """
        mock_repo.get_by_id.return_value = None

        result = GetSearchConfigByIdUseCase(mock_repo).execute(999)

        assert result is None


class TestGetSearchConfigsByUserIdUseCase:
    """Tests for GetSearchConfigsByUserIdUseCase.execute"""

    def test_execute_returns_list_of_entities(self, mock_repo, sample_entity):
        """
        Given: A user_id with existing configs
        When: execute is called
        Then: Returns list of entities
        """
        mock_repo.get_by_user_id.return_value = [sample_entity]

        result = GetSearchConfigsByUserIdUseCase(mock_repo).execute(1)

        mock_repo.get_by_user_id.assert_called_once_with(1)
        assert result == [sample_entity]

    def test_execute_returns_empty_list_when_no_configs(self, mock_repo):
        """
        Given: A user_id with no configs
        When: execute is called
        Then: Returns empty list
        """
        mock_repo.get_by_user_id.return_value = []

        result = GetSearchConfigsByUserIdUseCase(mock_repo).execute(99)

        assert result == []


class TestListSearchConfigsUseCase:
    """Tests for ListSearchConfigsUseCase.execute"""

    def test_execute_returns_paginated_result(self, mock_repo, sample_entity):
        """
        Given: Multiple configs in repo
        When: execute is called with pagination
        Then: Returns (list, total) tuple
        """
        mock_repo.get_all.return_value = ([sample_entity], 1)

        result, total = ListSearchConfigsUseCase(mock_repo).execute(limit=10, offset=0)

        mock_repo.get_all.assert_called_once_with(
            limit=10,
            offset=0,
            sort_by=None,
            sort_order=None,
            user_id=None,
            search_term=None,
        )
        assert total == 1
        assert result == [sample_entity]

    def test_execute_passes_sorting_params(self, mock_repo):
        """
        Given: sort_by and sort_order provided
        When: execute is called
        Then: Passes those params to repo
        """
        mock_repo.get_all.return_value = ([], 0)

        ListSearchConfigsUseCase(mock_repo).execute(
            limit=5,
            offset=0,
            sort_by="created_at",
            sort_order="desc",
            user_id=None,
            search_term=None,
        )

        mock_repo.get_all.assert_called_once_with(
            limit=5,
            offset=0,
            sort_by="created_at",
            sort_order="desc",
            user_id=None,
            search_term=None,
        )


class TestUpdateSearchConfigUseCase:
    """Tests for UpdateSearchConfigUseCase.execute"""

    def test_execute_returns_updated_entity(self, mock_repo, sample_entity):
        """
        Given: Existing id and updated entity
        When: execute is called
        Then: Returns updated entity
        """
        updated = SearchConfigEntity(
            id=1,
            search_term="iPhone 14",
            is_active=True,
            frequency_days=3,
            preferred_time=time(0, 0),
            user_id=1,
            source_website_ids=[],
        )
        mock_repo.update.return_value = updated

        result = UpdateSearchConfigUseCase(mock_repo).execute(1, sample_entity)

        mock_repo.update.assert_called_once_with(1, sample_entity)
        assert result == updated

    def test_execute_returns_none_when_not_found(self, mock_repo, sample_entity):
        """
        Given: Non-existent id
        When: execute is called
        Then: Returns None
        """
        mock_repo.update.return_value = None

        result = UpdateSearchConfigUseCase(mock_repo).execute(999, sample_entity)

        assert result is None


class TestDeleteSearchConfigUseCase:
    """Tests for DeleteSearchConfigUseCase.execute"""

    def test_execute_returns_true_when_deleted(self, mock_repo):
        """
        Given: Existing id
        When: execute is called
        Then: Returns True
        """
        mock_repo.delete.return_value = True

        result = DeleteSearchConfigUseCase(mock_repo).execute(1)

        mock_repo.delete.assert_called_once_with(1)
        assert result is True

    def test_execute_returns_false_when_not_found(self, mock_repo):
        """
        Given: Non-existent id
        When: execute is called
        Then: Returns False
        """
        mock_repo.delete.return_value = False

        result = DeleteSearchConfigUseCase(mock_repo).execute(999)

        assert result is False
