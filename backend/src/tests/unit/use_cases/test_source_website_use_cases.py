"""Unit tests for SourceWebsite Use Cases."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.app.stores.entities import Store
from src.app.use_cases.source_website_use_cases import (
    CreateSourceWebsiteUseCase,
    DeleteSourceWebsiteUseCase,
    GetSourceWebsiteByIdUseCase,
    GetSourceWebsiteByNameUseCase,
    ListSourceWebsitesUseCase,
    UpdateSourceWebsiteUseCase,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_source_website_repo():
    return Mock()


@pytest.fixture
def sample_source_website_entity():
    return Store(
        id=1,
        name="OLX",
        base_url="https://www.olx.com.br",
        is_active=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def sample_new_source_website_entity():
    """Entity without id (before persistence)."""
    return Store(
        name="Enjoei",
        base_url="https://www.enjoei.com.br",
        is_active=True,
    )


# ============================================================================
# Tests
# ============================================================================


class TestCreateSourceWebsiteUseCase:
    """Tests for CreateSourceWebsiteUseCase.execute"""

    def test_execute_should_create_and_return_entity(
        self, mock_source_website_repo, sample_new_source_website_entity
    ):
        """
        Given: A new source website entity and a mock repository
        When: execute is called
        Then: Repository.create is called and entity is returned
        """
        expected = Store(
            id=1,
            name="Enjoei",
            base_url="https://www.enjoei.com.br",
            is_active=True,
        )
        mock_source_website_repo.create.return_value = expected

        use_case = CreateSourceWebsiteUseCase(mock_source_website_repo)
        result = use_case.execute(sample_new_source_website_entity)

        mock_source_website_repo.create.assert_called_once_with(
            sample_new_source_website_entity
        )
        assert result == expected

    def test_execute_should_return_entity_with_generated_id(
        self, mock_source_website_repo, sample_new_source_website_entity
    ):
        """
        Given: A new entity (id=None) is passed to the repository
        When: execute is called
        Then: Returns entity with id assigned by the repository
        """
        persisted = Store(
            id=42,
            name=sample_new_source_website_entity.name,
            base_url=sample_new_source_website_entity.base_url,
            is_active=sample_new_source_website_entity.is_active,
        )
        mock_source_website_repo.create.return_value = persisted

        use_case = CreateSourceWebsiteUseCase(mock_source_website_repo)
        result = use_case.execute(sample_new_source_website_entity)

        assert result.id == 42


class TestGetSourceWebsiteByIdUseCase:
    """Tests for GetSourceWebsiteByIdUseCase.execute"""

    def test_execute_with_existing_id_should_return_entity(
        self, mock_source_website_repo, sample_source_website_entity
    ):
        """
        Given: A source website with the given ID exists
        When: execute is called with that ID
        Then: Returns the corresponding entity
        """
        mock_source_website_repo.get_by_id.return_value = sample_source_website_entity

        use_case = GetSourceWebsiteByIdUseCase(mock_source_website_repo)
        result = use_case.execute(1)

        mock_source_website_repo.get_by_id.assert_called_once_with(1)
        assert result == sample_source_website_entity

    def test_execute_with_nonexistent_id_should_return_none(
        self, mock_source_website_repo
    ):
        """
        Given: No source website with the given ID exists
        When: execute is called
        Then: Returns None
        """
        mock_source_website_repo.get_by_id.return_value = None

        use_case = GetSourceWebsiteByIdUseCase(mock_source_website_repo)
        result = use_case.execute(99999)

        assert result is None


class TestGetSourceWebsiteByNameUseCase:
    """Tests for GetSourceWebsiteByNameUseCase.execute"""

    def test_execute_with_existing_name_should_return_entity(
        self, mock_source_website_repo, sample_source_website_entity
    ):
        """
        Given: A source website with the given name exists
        When: execute is called with that name
        Then: Returns the corresponding entity
        """
        mock_source_website_repo.get_by_name.return_value = sample_source_website_entity

        use_case = GetSourceWebsiteByNameUseCase(mock_source_website_repo)
        result = use_case.execute("OLX")

        mock_source_website_repo.get_by_name.assert_called_once_with("OLX")
        assert result.name == "OLX"

    def test_execute_with_nonexistent_name_should_return_none(
        self, mock_source_website_repo
    ):
        """
        Given: No source website with the given name exists
        When: execute is called
        Then: Returns None
        """
        mock_source_website_repo.get_by_name.return_value = None

        use_case = GetSourceWebsiteByNameUseCase(mock_source_website_repo)
        result = use_case.execute("Nonexistent")

        assert result is None


class TestListSourceWebsitesUseCase:
    """Tests for ListSourceWebsitesUseCase.execute"""

    def test_execute_should_return_entities_and_total(
        self, mock_source_website_repo, sample_source_website_entity
    ):
        """
        Given: Repository returns a list of entities and a total
        When: execute is called
        Then: Returns (list, total) tuple
        """
        mock_source_website_repo.get_all.return_value = (
            [sample_source_website_entity],
            1,
        )

        use_case = ListSourceWebsitesUseCase(mock_source_website_repo)
        result, total = use_case.execute()

        assert len(result) == 1
        assert total == 1

    def test_execute_with_pagination_params_should_pass_to_repository(
        self, mock_source_website_repo
    ):
        """
        Given: Pagination params are provided
        When: execute is called
        Then: Repository.get_all is called with the correct params
        """
        mock_source_website_repo.get_all.return_value = ([], 0)

        use_case = ListSourceWebsitesUseCase(mock_source_website_repo)
        use_case.execute(limit=5, offset=10, sort_by="name", sort_order="asc")

        mock_source_website_repo.get_all.assert_called_once_with(
            limit=5, offset=10, sort_by="name", sort_order="asc"
        )

    def test_execute_with_empty_repository_should_return_empty_list(
        self, mock_source_website_repo
    ):
        """
        Given: Repository has no source websites
        When: execute is called
        Then: Returns empty list and total=0
        """
        mock_source_website_repo.get_all.return_value = ([], 0)

        use_case = ListSourceWebsitesUseCase(mock_source_website_repo)
        result, total = use_case.execute()

        assert result == []
        assert total == 0


class TestUpdateSourceWebsiteUseCase:
    """Tests for UpdateSourceWebsiteUseCase.execute"""

    def test_execute_with_existing_entity_should_return_updated_entity(
        self, mock_source_website_repo, sample_source_website_entity
    ):
        """
        Given: An existing source website
        When: execute is called with updated data
        Then: Returns updated entity
        """
        updated = Store(
            id=1, name="OLX Brasil", base_url="https://www.olx.com.br", is_active=True
        )
        mock_source_website_repo.update.return_value = updated

        use_case = UpdateSourceWebsiteUseCase(mock_source_website_repo)
        result = use_case.execute(1, sample_source_website_entity)

        assert result.name == "OLX Brasil"

    def test_execute_with_nonexistent_entity_should_return_none(
        self, mock_source_website_repo, sample_source_website_entity
    ):
        """
        Given: No source website with the given ID exists
        When: execute is called
        Then: Returns None
        """
        mock_source_website_repo.update.return_value = None

        use_case = UpdateSourceWebsiteUseCase(mock_source_website_repo)
        result = use_case.execute(99999, sample_source_website_entity)

        assert result is None


class TestDeleteSourceWebsiteUseCase:
    """Tests for DeleteSourceWebsiteUseCase.execute"""

    def test_execute_with_existing_entity_should_return_true(
        self, mock_source_website_repo
    ):
        """
        Given: A source website with the given ID exists
        When: execute is called
        Then: Returns True
        """
        mock_source_website_repo.delete.return_value = True

        use_case = DeleteSourceWebsiteUseCase(mock_source_website_repo)
        result = use_case.execute(1)

        assert result is True

    def test_execute_with_nonexistent_entity_should_return_false(
        self, mock_source_website_repo
    ):
        """
        Given: No source website with the given ID exists
        When: execute is called
        Then: Returns False
        """
        mock_source_website_repo.delete.return_value = False

        use_case = DeleteSourceWebsiteUseCase(mock_source_website_repo)
        result = use_case.execute(99999)

        assert result is False
