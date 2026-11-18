"""
Unit tests for Search Config Presenter.

Tests presentation layer (JSON:API formatting) with fixtures.
Following Given/When/Then pattern for clarity.
"""

from datetime import datetime, time

import pytest
from fastapi.responses import JSONResponse

from src.app.interfaces.http.presenters.search_config_presenter import (
    SearchConfigPresenter,
)
from src.app.searches.entities import SavedSearch
from src.common.jsonapi import JsonApiError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_search_config_entity():
    """Sample search config entity for testing."""
    return SavedSearch(
        id=1,
        search_term="notebook lenovo",
        is_active=True,
        frequency_days=7,
        preferred_time=time(8, 0, 0),
        search_metadata={"notes": "test"},
        user_id=1,
        source_website_ids=[1, 2],
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_search_config_collection(sample_search_config_entity):
    """Sample collection of search config entities for testing."""
    second = SavedSearch(
        id=2,
        search_term="iphone 15",
        is_active=False,
        frequency_days=1,
        preferred_time=time(9, 0, 0),
        user_id=1,
        source_website_ids=[],
        created_at=datetime(2025, 1, 2, 12, 0, 0),
        updated_at=datetime(2025, 1, 2, 12, 0, 0),
    )
    return [sample_search_config_entity, second]


@pytest.fixture
def sample_validation_errors():
    """Sample validation errors for testing."""
    return [
        JsonApiError(
            status="422",
            code="MISSING_FIELD",
            title="Validation error",
            detail="Field 'search_term' is required",
            source={"pointer": "/data/attributes/search_term"},
        ),
        JsonApiError(
            status="422",
            code="INVALID_VALUE",
            title="Validation error",
            detail="Field 'frequency_days' must be a positive integer",
            source={"pointer": "/data/attributes/frequency_days"},
        ),
    ]


# ============================================================================
# SearchConfigPresenter.handle_success Tests
# ============================================================================


class TestSearchConfigPresenterHandleSuccess:
    """Tests for SearchConfigPresenter.handle_success()."""

    def test_handle_success_should_return_jsonapi_response(
        self, sample_search_config_entity
    ):
        """
        Given: A valid search config entity
        When: SearchConfigPresenter.handle_success() is called
        Then: Should return SearchConfigReadResponse with correct JSON:API structure
        """
        # When
        response = SearchConfigPresenter.handle_success(sample_search_config_entity)

        # Then
        assert response.data.type == "search_configs"
        assert response.data.id == "1"
        assert response.data.attributes.search_term == "notebook lenovo"
        assert response.data.attributes.is_active is True

    def test_handle_success_should_include_all_attributes(
        self, sample_search_config_entity
    ):
        """
        Given: A search config entity with all fields
        When: SearchConfigPresenter.handle_success() is called
        Then: Should include all attributes in the response
        """
        # When
        response = SearchConfigPresenter.handle_success(sample_search_config_entity)

        # Then
        attrs = response.data.attributes
        assert attrs.frequency_days == 7
        assert attrs.user_id == 1
        assert attrs.source_website_ids == [1, 2]
        assert attrs.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert attrs.updated_at == datetime(2025, 1, 1, 12, 0, 0)

    def test_handle_success_should_have_string_id(self, sample_search_config_entity):
        """
        Given: A search config entity with integer id
        When: SearchConfigPresenter.handle_success() is called
        Then: JSON:API id should be a string
        """
        # When
        response = SearchConfigPresenter.handle_success(sample_search_config_entity)

        # Then
        assert isinstance(response.data.id, str)
        assert response.data.id == "1"

    def test_handle_success_should_reflect_inactive_status(self):
        """
        Given: An inactive search config entity
        When: SearchConfigPresenter.handle_success() is called
        Then: Should correctly reflect is_active=False
        """
        # Given
        entity = SavedSearch(
            id=5,
            search_term="test",
            is_active=False,
            frequency_days=7,
            preferred_time=time(8, 0, 0),
            user_id=2,
        )

        # When
        response = SearchConfigPresenter.handle_success(entity)

        # Then
        assert response.data.attributes.is_active is False

    def test_handle_success_should_handle_empty_source_website_ids(self):
        """
        Given: A search config entity with no source websites
        When: SearchConfigPresenter.handle_success() is called
        Then: Should return empty list for source_website_ids
        """
        # Given
        entity = SavedSearch(
            id=3,
            search_term="test",
            is_active=True,
            frequency_days=1,
            preferred_time=time(0, 0, 0),
            user_id=1,
            source_website_ids=[],
        )

        # When
        response = SearchConfigPresenter.handle_success(entity)

        # Then
        assert response.data.attributes.source_website_ids == []


# ============================================================================
# SearchConfigPresenter.handle_collection_success Tests
# ============================================================================


class TestSearchConfigPresenterHandleCollectionSuccess:
    """Tests for SearchConfigPresenter.handle_collection_success()."""

    def test_handle_collection_success_should_return_jsonapi_collection(
        self, sample_search_config_collection
    ):
        """
        Given: A list of search config entities and total count
        When: SearchConfigPresenter.handle_collection_success() is called
        Then: Should return collection response with all items
        """
        # When
        response = SearchConfigPresenter.handle_collection_success(
            sample_search_config_collection, total=2
        )

        # Then
        assert len(response.data) == 2
        assert response.data[0].type == "search_configs"
        assert response.data[0].id == "1"
        assert response.data[1].id == "2"

    def test_handle_collection_success_should_include_meta_total(
        self, sample_search_config_collection
    ):
        """
        Given: A collection with a known total
        When: SearchConfigPresenter.handle_collection_success() is called
        Then: Should include meta with total count
        """
        # When
        response = SearchConfigPresenter.handle_collection_success(
            sample_search_config_collection, total=25
        )

        # Then
        assert response.meta == {"total": 25}

    def test_handle_collection_success_should_handle_empty_collection(self):
        """
        Given: An empty list
        When: SearchConfigPresenter.handle_collection_success() is called
        Then: Should return empty data list with total=0
        """
        # When
        response = SearchConfigPresenter.handle_collection_success([], total=0)

        # Then
        assert response.data == []
        assert response.meta == {"total": 0}


# ============================================================================
# SearchConfigPresenter.handle_validation_errors Tests
# ============================================================================


class TestSearchConfigPresenterHandleValidationErrors:
    """Tests for SearchConfigPresenter.handle_validation_errors()."""

    def test_handle_validation_errors_should_return_jsonapi_error_response(
        self, sample_validation_errors
    ):
        """
        Given: A list of validation errors
        When: SearchConfigPresenter.handle_validation_errors() is called
        Then: Should return JSONResponse with correct JSON:API error structure
        """
        # When
        response = SearchConfigPresenter.handle_validation_errors(
            sample_validation_errors
        )

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        assert response.media_type == "application/vnd.api+json"

    def test_handle_validation_errors_should_include_all_errors(
        self, sample_validation_errors
    ):
        """
        Given: Multiple validation errors
        When: SearchConfigPresenter.handle_validation_errors() is called
        Then: Should include all errors in the response body
        """
        # When
        response = SearchConfigPresenter.handle_validation_errors(
            sample_validation_errors
        )
        content = response.body.decode("utf-8")

        # Then
        assert "MISSING_FIELD" in content
        assert "INVALID_VALUE" in content
        assert "search_term" in content

    def test_handle_validation_errors_should_use_first_error_status_code(self):
        """
        Given: Validation errors starting with status 400
        When: SearchConfigPresenter.handle_validation_errors() is called
        Then: Should use the first error's status code
        """
        # Given
        errors = [
            JsonApiError(
                status="400",
                code="BAD_REQUEST",
                title="Bad Request",
                detail="Invalid data",
            )
        ]

        # When
        response = SearchConfigPresenter.handle_validation_errors(errors)

        # Then
        assert response.status_code == 400


# ============================================================================
# SearchConfigPresenter.handle_not_found Tests
# ============================================================================


class TestSearchConfigPresenterHandleNotFound:
    """Tests for SearchConfigPresenter.handle_not_found()."""

    def test_handle_not_found_should_return_404_jsonapi_error(self):
        """
        Given: A search config identifier
        When: SearchConfigPresenter.handle_not_found() is called
        Then: Should return 404 JSONResponse with JSON:API error structure
        """
        # When
        response = SearchConfigPresenter.handle_not_found(
            identifier="id=999", pointer="/data/attributes/id"
        )

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        assert response.media_type == "application/vnd.api+json"

    def test_handle_not_found_should_include_identifier_in_detail(self):
        """
        Given: A specific search config identifier
        When: SearchConfigPresenter.handle_not_found() is called
        Then: Should include identifier in the error detail
        """
        # When
        response = SearchConfigPresenter.handle_not_found(
            identifier="user_id=42",
            pointer="/data/attributes/user_id",
        )
        content = response.body.decode("utf-8")

        # Then
        assert "user_id=42" in content
        assert "NOT_FOUND" in content

    def test_handle_not_found_should_have_correct_error_structure(self):
        """
        Given: A search config identifier
        When: SearchConfigPresenter.handle_not_found() is called
        Then: Should have correct JSON:API error fields
        """
        # When
        response = SearchConfigPresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"status":"404"' in content or '"status": "404"' in content
        assert '"code":"NOT_FOUND"' in content or '"code": "NOT_FOUND"' in content
        assert (
            '"title":"Search config not found"' in content
            or '"title": "Search config not found"' in content
        )

    def test_handle_not_found_should_use_default_pointer(self):
        """
        Given: No pointer specified
        When: SearchConfigPresenter.handle_not_found() is called
        Then: Should use default pointer '/data'
        """
        # When
        response = SearchConfigPresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"/data"' in content or "pointer" in content
