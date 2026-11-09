"""Unit tests for PriceHistory Use Cases."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.app.catalog.entities import PriceHistory as PriceHistoryEntity
from src.app.catalog.use_cases import (
    CreatePriceHistoryUseCase,
    DeletePriceHistoryUseCase,
    GetLatestPriceByProductIdUseCase,
    GetPriceHistoryByIdUseCase,
    GetPriceHistoryByProductIdUseCase,
    ListPriceHistoriesUseCase,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_price_history_repo():
    return Mock()


@pytest.fixture
def sample_price_history_entity():
    return PriceHistoryEntity(
        id=1,
        product_id=10,
        price=299.99,
        created_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def sample_new_price_history_entity():
    return PriceHistoryEntity(product_id=10, price=299.99)


# ============================================================================
# Tests
# ============================================================================


class TestCreatePriceHistoryUseCase:
    def test_execute_should_create_and_return_entity(
        self, mock_price_history_repo, sample_new_price_history_entity
    ):
        """
        Given: A new price history entity and a mock repository
        When: execute is called
        Then: Repository.create is called and entity is returned with id
        """
        expected = PriceHistoryEntity(id=1, product_id=10, price=299.99)
        mock_price_history_repo.create.return_value = expected

        use_case = CreatePriceHistoryUseCase(mock_price_history_repo)
        result = use_case.execute(sample_new_price_history_entity)

        mock_price_history_repo.create.assert_called_once_with(
            sample_new_price_history_entity
        )
        assert result.id == 1

    def test_execute_returns_entity_with_generated_id(
        self, mock_price_history_repo, sample_new_price_history_entity
    ):
        mock_price_history_repo.create.return_value = PriceHistoryEntity(
            id=42, product_id=10, price=299.99
        )
        result = CreatePriceHistoryUseCase(mock_price_history_repo).execute(
            sample_new_price_history_entity
        )
        assert result.id == 42


class TestGetPriceHistoryByIdUseCase:
    def test_execute_with_existing_id_returns_entity(
        self, mock_price_history_repo, sample_price_history_entity
    ):
        mock_price_history_repo.get_by_id.return_value = sample_price_history_entity

        result = GetPriceHistoryByIdUseCase(mock_price_history_repo).execute(1)

        mock_price_history_repo.get_by_id.assert_called_once_with(1)
        assert result == sample_price_history_entity

    def test_execute_with_nonexistent_id_returns_none(self, mock_price_history_repo):
        mock_price_history_repo.get_by_id.return_value = None

        result = GetPriceHistoryByIdUseCase(mock_price_history_repo).execute(99999)

        assert result is None


class TestGetPriceHistoryByProductIdUseCase:
    def test_execute_returns_list_of_entities(
        self, mock_price_history_repo, sample_price_history_entity
    ):
        mock_price_history_repo.get_by_product_id.return_value = [
            sample_price_history_entity
        ]

        result = GetPriceHistoryByProductIdUseCase(mock_price_history_repo).execute(10)

        mock_price_history_repo.get_by_product_id.assert_called_once_with(10)
        assert len(result) == 1

    def test_execute_with_no_records_returns_empty_list(self, mock_price_history_repo):
        mock_price_history_repo.get_by_product_id.return_value = []

        result = GetPriceHistoryByProductIdUseCase(mock_price_history_repo).execute(
            99999
        )

        assert result == []


class TestGetLatestPriceByProductIdUseCase:
    def test_execute_returns_latest_entity(
        self, mock_price_history_repo, sample_price_history_entity
    ):
        mock_price_history_repo.get_latest_by_product_id.return_value = (
            sample_price_history_entity
        )

        result = GetLatestPriceByProductIdUseCase(mock_price_history_repo).execute(10)

        mock_price_history_repo.get_latest_by_product_id.assert_called_once_with(10)
        assert result == sample_price_history_entity

    def test_execute_with_no_records_returns_none(self, mock_price_history_repo):
        mock_price_history_repo.get_latest_by_product_id.return_value = None

        result = GetLatestPriceByProductIdUseCase(mock_price_history_repo).execute(
            99999
        )

        assert result is None


class TestListPriceHistoriesUseCase:
    def test_execute_returns_entities_and_total(
        self, mock_price_history_repo, sample_price_history_entity
    ):
        mock_price_history_repo.get_all.return_value = (
            [sample_price_history_entity],
            1,
        )

        result, total = ListPriceHistoriesUseCase(mock_price_history_repo).execute()

        assert len(result) == 1
        assert total == 1

    def test_execute_passes_pagination_params_to_repository(
        self, mock_price_history_repo
    ):
        mock_price_history_repo.get_all.return_value = ([], 0)

        ListPriceHistoriesUseCase(mock_price_history_repo).execute(
            limit=5, offset=10, sort_by="price", sort_order="asc"
        )

        mock_price_history_repo.get_all.assert_called_once_with(
            limit=5, offset=10, sort_by="price", sort_order="asc"
        )

    def test_execute_with_empty_repository_returns_empty_list(
        self, mock_price_history_repo
    ):
        mock_price_history_repo.get_all.return_value = ([], 0)

        result, total = ListPriceHistoriesUseCase(mock_price_history_repo).execute()

        assert result == []
        assert total == 0


class TestDeletePriceHistoryUseCase:
    def test_execute_with_existing_id_returns_true(self, mock_price_history_repo):
        mock_price_history_repo.delete.return_value = True

        result = DeletePriceHistoryUseCase(mock_price_history_repo).execute(1)

        assert result is True

    def test_execute_with_nonexistent_id_returns_false(self, mock_price_history_repo):
        mock_price_history_repo.delete.return_value = False

        result = DeletePriceHistoryUseCase(mock_price_history_repo).execute(99999)

        assert result is False
