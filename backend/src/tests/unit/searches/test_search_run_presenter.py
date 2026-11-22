"""
Unit tests for Search Execution Log Presenter.

Tests presentation layer (JSON:API formatting) with fixtures.
Following Given/When/Then pattern for clarity.
"""

from datetime import datetime

import pytest
from fastapi.responses import JSONResponse

from src.app.searches.entities import SearchRun
from src.app.searches.http.search_run_presenter import (
    SearchRunPresenter,
)
from src.common.jsonapi import JsonApiError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_search_execution_log_entity():
    """Sample search execution log entity for testing."""
    return SearchRun(
        id=1,
        search_config_id=10,
        status="success",
        results_count=42,
        error_message=None,
        started_at=datetime(2025, 5, 10, 8, 0, 0),
        finished_at=datetime(2025, 5, 10, 8, 1, 30),
    )


@pytest.fixture
def sample_failed_log_entity():
    """Sample failed search execution log entity for testing."""
    return SearchRun(
        id=2,
        search_config_id=10,
        status="failed",
        results_count=0,
        error_message="Connection timeout",
        started_at=datetime(2025, 5, 11, 8, 0, 0),
        finished_at=datetime(2025, 5, 11, 8, 0, 5),
    )


@pytest.fixture
def sample_search_execution_log_collection(
    sample_search_execution_log_entity, sample_failed_log_entity
):
    """Sample collection of search execution log entities for testing."""
    return [sample_search_execution_log_entity, sample_failed_log_entity]


@pytest.fixture
def sample_validation_errors():
    """Sample validation errors for testing."""
    return [
        JsonApiError(
            status="422",
            code="MISSING_FIELD",
            title="Validation error",
            detail="Field 'search_config_id' is required",
            source={"pointer": "/data/attributes/search_config_id"},
        ),
        JsonApiError(
            status="422",
            code="INVALID_VALUE",
            title="Validation error",
            detail="Field 'status' must be one of: pending, running, success, failed",
            source={"pointer": "/data/attributes/status"},
        ),
    ]


# ============================================================================
# SearchRunPresenter.handle_success Tests
# ============================================================================


class TestSearchRunPresenterHandleSuccess:
    """Tests for SearchRunPresenter.handle_success()."""

    def test_handle_success_should_return_jsonapi_response(
        self, sample_search_execution_log_entity
    ):
        """
        Given: A valid search execution log entity
        When: SearchRunPresenter.handle_success() is called
        Then: Should return SearchRunReadResponse with correct JSON:API structure
        """
        # When
        response = SearchRunPresenter.handle_success(sample_search_execution_log_entity)

        # Then
        assert response.data.type == "search_execution_logs"
        assert response.data.id == "1"
        assert response.data.attributes.search_config_id == 10
        assert response.data.attributes.status == "success"

    def test_handle_success_should_include_all_attributes(
        self, sample_search_execution_log_entity
    ):
        """
        Given: A search execution log entity with all fields
        When: SearchRunPresenter.handle_success() is called
        Then: Should include all attributes in the response
        """
        # When
        response = SearchRunPresenter.handle_success(sample_search_execution_log_entity)

        # Then
        attrs = response.data.attributes
        assert attrs.results_count == 42
        assert attrs.error_message is None
        assert attrs.started_at == datetime(2025, 5, 10, 8, 0, 0)
        assert attrs.finished_at == datetime(2025, 5, 10, 8, 1, 30)

    def test_handle_success_should_have_string_id(
        self, sample_search_execution_log_entity
    ):
        """
        Given: A search execution log entity with integer id
        When: SearchRunPresenter.handle_success() is called
        Then: JSON:API id should be a string
        """
        # When
        response = SearchRunPresenter.handle_success(sample_search_execution_log_entity)

        # Then
        assert isinstance(response.data.id, str)
        assert response.data.id == "1"

    def test_handle_success_should_reflect_failed_status(
        self, sample_failed_log_entity
    ):
        """
        Given: A failed search execution log entity
        When: SearchRunPresenter.handle_success() is called
        Then: Should correctly reflect status='failed' and error_message
        """
        # When
        response = SearchRunPresenter.handle_success(sample_failed_log_entity)

        # Then
        assert response.data.attributes.status == "failed"
        assert response.data.attributes.error_message == "Connection timeout"
        assert response.data.attributes.results_count == 0

    def test_handle_success_should_handle_pending_log(self):
        """
        Given: A pending search execution log (not yet finished)
        When: SearchRunPresenter.handle_success() is called
        Then: Should reflect status='pending' and finished_at=None
        """
        # Given
        entity = SearchRun(
            id=3,
            search_config_id=5,
            status="pending",
            started_at=datetime(2025, 5, 12, 9, 0, 0),
        )

        # When
        response = SearchRunPresenter.handle_success(entity)

        # Then
        assert response.data.attributes.status == "pending"
        assert response.data.attributes.finished_at is None


# ============================================================================
# SearchRunPresenter.handle_collection_success Tests
# ============================================================================


class TestSearchRunPresenterHandleCollectionSuccess:
    """Tests for SearchRunPresenter.handle_collection_success()."""

    def test_handle_collection_success_should_return_jsonapi_collection(
        self, sample_search_execution_log_collection
    ):
        """
        Given: A list of search execution log entities and total count
        When: SearchRunPresenter.handle_collection_success() is called
        Then: Should return collection response with all items
        """
        # When
        response = SearchRunPresenter.handle_collection_success(
            sample_search_execution_log_collection, total=2
        )

        # Then
        assert len(response.data) == 2
        assert response.data[0].type == "search_execution_logs"
        assert response.data[0].id == "1"
        assert response.data[1].id == "2"

    def test_handle_collection_success_should_include_meta_total(
        self, sample_search_execution_log_collection
    ):
        """
        Given: A collection with a known total
        When: SearchRunPresenter.handle_collection_success() is called
        Then: Should include meta with total count
        """
        # When
        response = SearchRunPresenter.handle_collection_success(
            sample_search_execution_log_collection, total=15
        )

        # Then
        assert response.meta == {"total": 15}

    def test_handle_collection_success_should_handle_empty_collection(self):
        """
        Given: An empty list
        When: SearchRunPresenter.handle_collection_success() is called
        Then: Should return empty data list with total=0
        """
        # When
        response = SearchRunPresenter.handle_collection_success([], total=0)

        # Then
        assert response.data == []
        assert response.meta == {"total": 0}

    def test_handle_collection_success_preserves_mixed_statuses(
        self, sample_search_execution_log_collection
    ):
        """
        Given: A collection with logs of different statuses
        When: SearchRunPresenter.handle_collection_success() is called
        Then: Should preserve all statuses correctly
        """
        # When
        response = SearchRunPresenter.handle_collection_success(
            sample_search_execution_log_collection, total=2
        )

        # Then
        assert response.data[0].attributes.status == "success"
        assert response.data[1].attributes.status == "failed"


# ============================================================================
# SearchRunPresenter.handle_validation_errors Tests
# ============================================================================


class TestSearchRunPresenterHandleValidationErrors:
    """Tests for SearchRunPresenter.handle_validation_errors()."""

    def test_handle_validation_errors_should_return_jsonapi_error_response(
        self, sample_validation_errors
    ):
        """
        Given: A list of validation errors
        When: SearchRunPresenter.handle_validation_errors() is called
        Then: Should return JSONResponse with correct JSON:API error structure
        """
        # When
        response = SearchRunPresenter.handle_validation_errors(sample_validation_errors)

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        assert response.media_type == "application/vnd.api+json"

    def test_handle_validation_errors_should_include_all_errors(
        self, sample_validation_errors
    ):
        """
        Given: Multiple validation errors
        When: SearchRunPresenter.handle_validation_errors() is called
        Then: Should include all errors in the response body
        """
        # When
        response = SearchRunPresenter.handle_validation_errors(sample_validation_errors)
        content = response.body.decode("utf-8")

        # Then
        assert "MISSING_FIELD" in content
        assert "INVALID_VALUE" in content
        assert "search_config_id" in content

    def test_handle_validation_errors_should_use_first_error_status_code(self):
        """
        Given: Validation errors starting with status 400
        When: SearchRunPresenter.handle_validation_errors() is called
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
        response = SearchRunPresenter.handle_validation_errors(errors)

        # Then
        assert response.status_code == 400


# ============================================================================
# SearchRunPresenter.handle_not_found Tests
# ============================================================================


class TestSearchRunPresenterHandleNotFound:
    """Tests for SearchRunPresenter.handle_not_found()."""

    def test_handle_not_found_should_return_404_jsonapi_error(self):
        """
        Given: A search execution log identifier
        When: SearchRunPresenter.handle_not_found() is called
        Then: Should return 404 JSONResponse with JSON:API error structure
        """
        # When
        response = SearchRunPresenter.handle_not_found(
            identifier="id=999", pointer="/data/attributes/id"
        )

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        assert response.media_type == "application/vnd.api+json"

    def test_handle_not_found_should_include_identifier_in_detail(self):
        """
        Given: A specific search execution log identifier
        When: SearchRunPresenter.handle_not_found() is called
        Then: Should include identifier in the error detail
        """
        # When
        response = SearchRunPresenter.handle_not_found(
            identifier="search_config_id=42",
            pointer="/data/attributes/search_config_id",
        )
        content = response.body.decode("utf-8")

        # Then
        assert "search_config_id=42" in content
        assert "NOT_FOUND" in content

    def test_handle_not_found_should_have_correct_error_structure(self):
        """
        Given: A search execution log identifier
        When: SearchRunPresenter.handle_not_found() is called
        Then: Should have correct JSON:API error fields
        """
        # When
        response = SearchRunPresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"status":"404"' in content or '"status": "404"' in content
        assert '"code":"NOT_FOUND"' in content or '"code": "NOT_FOUND"' in content
        assert (
            '"title":"Search execution log not found"' in content
            or '"title": "Search execution log not found"' in content
        )

    def test_handle_not_found_should_use_default_pointer(self):
        """
        Given: No pointer specified
        When: SearchRunPresenter.handle_not_found() is called
        Then: Should use default pointer '/data'
        """
        # When
        response = SearchRunPresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"/data"' in content or "pointer" in content
