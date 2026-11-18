"""Unit tests for SearchExecutionLog Use Cases."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.app.searches.entities import SearchRun
from src.app.use_cases.search_execution_log_use_cases import (
    CreateSearchExecutionLogUseCase,
    DeleteSearchExecutionLogUseCase,
    GetSearchExecutionLogByIdUseCase,
    GetSearchExecutionLogsBySearchConfigIdUseCase,
    ListSearchExecutionLogsUseCase,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_search_execution_log_repo():
    return Mock()


@pytest.fixture
def sample_search_execution_log_entity():
    return SearchRun(
        id=1,
        search_config_id=10,
        status="success",
        results_count=5,
        started_at=datetime(2024, 1, 1, tzinfo=UTC),
        finished_at=datetime(2024, 1, 1, 0, 5, tzinfo=UTC),
    )


@pytest.fixture
def sample_new_search_execution_log_entity():
    return SearchRun(search_config_id=10, status="pending")


# ============================================================================
# Tests
# ============================================================================


class TestCreateSearchExecutionLogUseCase:
    def test_execute_should_create_and_return_entity(
        self,
        mock_search_execution_log_repo,
        sample_new_search_execution_log_entity,
    ):
        """
        Given: A new search execution log entity and a mock repository
        When: execute is called
        Then: Repository.create is called and entity is returned with id
        """
        expected = SearchRun(id=1, search_config_id=10, status="pending")
        mock_search_execution_log_repo.create.return_value = expected

        use_case = CreateSearchExecutionLogUseCase(mock_search_execution_log_repo)
        result = use_case.execute(sample_new_search_execution_log_entity)

        mock_search_execution_log_repo.create.assert_called_once_with(
            sample_new_search_execution_log_entity
        )
        assert result.id == 1

    def test_execute_returns_entity_with_generated_id(
        self, mock_search_execution_log_repo, sample_new_search_execution_log_entity
    ):
        mock_search_execution_log_repo.create.return_value = SearchRun(
            id=42, search_config_id=10, status="pending"
        )
        result = CreateSearchExecutionLogUseCase(
            mock_search_execution_log_repo
        ).execute(sample_new_search_execution_log_entity)
        assert result.id == 42


class TestGetSearchExecutionLogByIdUseCase:
    def test_execute_with_existing_id_returns_entity(
        self,
        mock_search_execution_log_repo,
        sample_search_execution_log_entity,
    ):
        mock_search_execution_log_repo.get_by_id.return_value = (
            sample_search_execution_log_entity
        )

        result = GetSearchExecutionLogByIdUseCase(
            mock_search_execution_log_repo
        ).execute(1)

        mock_search_execution_log_repo.get_by_id.assert_called_once_with(1)
        assert result == sample_search_execution_log_entity

    def test_execute_with_nonexistent_id_returns_none(
        self, mock_search_execution_log_repo
    ):
        mock_search_execution_log_repo.get_by_id.return_value = None

        result = GetSearchExecutionLogByIdUseCase(
            mock_search_execution_log_repo
        ).execute(99999)

        assert result is None


class TestGetSearchExecutionLogsBySearchConfigIdUseCase:
    def test_execute_returns_list_of_entities(
        self,
        mock_search_execution_log_repo,
        sample_search_execution_log_entity,
    ):
        mock_search_execution_log_repo.get_by_search_config_id.return_value = [
            sample_search_execution_log_entity
        ]

        result = GetSearchExecutionLogsBySearchConfigIdUseCase(
            mock_search_execution_log_repo
        ).execute(10)

        mock_search_execution_log_repo.get_by_search_config_id.assert_called_once_with(
            10
        )
        assert len(result) == 1

    def test_execute_with_no_records_returns_empty_list(
        self, mock_search_execution_log_repo
    ):
        mock_search_execution_log_repo.get_by_search_config_id.return_value = []

        result = GetSearchExecutionLogsBySearchConfigIdUseCase(
            mock_search_execution_log_repo
        ).execute(99999)

        assert result == []


class TestListSearchExecutionLogsUseCase:
    def test_execute_returns_paginated_results(
        self,
        mock_search_execution_log_repo,
        sample_search_execution_log_entity,
    ):
        mock_search_execution_log_repo.get_all.return_value = (
            [sample_search_execution_log_entity],
            1,
        )

        result, total = ListSearchExecutionLogsUseCase(
            mock_search_execution_log_repo
        ).execute(limit=10, offset=0)

        mock_search_execution_log_repo.get_all.assert_called_once_with(
            limit=10, offset=0, sort_by=None, sort_order=None
        )
        assert total == 1
        assert len(result) == 1

    def test_execute_with_no_records_returns_empty_list(
        self, mock_search_execution_log_repo
    ):
        mock_search_execution_log_repo.get_all.return_value = ([], 0)

        result, total = ListSearchExecutionLogsUseCase(
            mock_search_execution_log_repo
        ).execute()

        assert result == []
        assert total == 0


class TestDeleteSearchExecutionLogUseCase:
    def test_execute_with_existing_id_returns_true(
        self, mock_search_execution_log_repo
    ):
        mock_search_execution_log_repo.delete.return_value = True

        result = DeleteSearchExecutionLogUseCase(
            mock_search_execution_log_repo
        ).execute(1)

        mock_search_execution_log_repo.delete.assert_called_once_with(1)
        assert result is True

    def test_execute_with_nonexistent_id_returns_false(
        self, mock_search_execution_log_repo
    ):
        mock_search_execution_log_repo.delete.return_value = False

        result = DeleteSearchExecutionLogUseCase(
            mock_search_execution_log_repo
        ).execute(99999)

        assert result is False
