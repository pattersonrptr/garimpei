"""
Unit tests for Source Website Presenter.

Tests presentation layer (JSON:API formatting) with fixtures.
Following Given/When/Then pattern for clarity.
"""

from datetime import datetime

import pytest
from fastapi.responses import JSONResponse

from src.app.stores.entities import Store
from src.app.stores.http.store_presenter import (
    StorePresenter,
)
from src.common.jsonapi import JsonApiError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_store_entity():
    """Sample source website entity for testing."""
    return Store(
        id=1,
        name="MercadoLivre",
        base_url="https://www.mercadolivre.com.br",
        is_active=True,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_store_collection(sample_store_entity):
    """Sample collection of source website entities for testing."""
    second = Store(
        id=2,
        name="OLX",
        base_url="https://www.olx.com.br",
        is_active=False,
        created_at=datetime(2025, 1, 2, 12, 0, 0),
        updated_at=datetime(2025, 1, 2, 12, 0, 0),
    )
    return [sample_store_entity, second]


@pytest.fixture
def sample_validation_errors():
    """Sample validation errors for testing."""
    return [
        JsonApiError(
            status="422",
            code="MISSING_FIELD",
            title="Validation error",
            detail="Field 'name' is required",
            source={"pointer": "/data/attributes/name"},
        ),
        JsonApiError(
            status="422",
            code="INVALID_URL",
            title="Validation error",
            detail="Field 'base_url' must be a valid URL",
            source={"pointer": "/data/attributes/base_url"},
        ),
    ]


# ============================================================================
# StorePresenter.handle_success Tests
# ============================================================================


class TestStorePresenterHandleSuccess:
    """Tests for StorePresenter.handle_success()."""

    def test_handle_success_should_return_jsonapi_response(self, sample_store_entity):
        """
        Given: A valid source website entity
        When: StorePresenter.handle_success() is called
        Then: Should return StoreReadResponse with correct JSON:API structure
        """
        # When
        response = StorePresenter.handle_success(sample_store_entity)

        # Then
        assert response.data.type == "source_websites"
        assert response.data.id == "1"
        assert response.data.attributes.name == "MercadoLivre"
        assert response.data.attributes.base_url == "https://www.mercadolivre.com.br"

    def test_handle_success_should_include_all_attributes(self, sample_store_entity):
        """
        Given: A source website entity with all fields
        When: StorePresenter.handle_success() is called
        Then: Should include all attributes in the response
        """
        # When
        response = StorePresenter.handle_success(sample_store_entity)

        # Then
        attrs = response.data.attributes
        assert attrs.is_active is True
        assert attrs.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert attrs.updated_at == datetime(2025, 1, 1, 12, 0, 0)

    def test_handle_success_should_have_string_id(self, sample_store_entity):
        """
        Given: A source website entity with integer id
        When: StorePresenter.handle_success() is called
        Then: JSON:API id should be a string
        """
        # When
        response = StorePresenter.handle_success(sample_store_entity)

        # Then
        assert isinstance(response.data.id, str)
        assert response.data.id == "1"

    def test_handle_success_should_reflect_inactive_status(self):
        """
        Given: An inactive source website entity
        When: StorePresenter.handle_success() is called
        Then: Should correctly reflect is_active=False
        """
        # Given
        entity = Store(
            id=3,
            name="Inactive Site",
            base_url="https://inactive.example.com",
            is_active=False,
        )

        # When
        response = StorePresenter.handle_success(entity)

        # Then
        assert response.data.attributes.is_active is False


# ============================================================================
# StorePresenter.handle_collection_success Tests
# ============================================================================


class TestStorePresenterHandleCollectionSuccess:
    """Tests for StorePresenter.handle_collection_success()."""

    def test_handle_collection_success_should_return_jsonapi_collection(
        self, sample_store_collection
    ):
        """
        Given: A list of source website entities and total count
        When: StorePresenter.handle_collection_success() is called
        Then: Should return collection response with all items
        """
        # When
        response = StorePresenter.handle_collection_success(
            sample_store_collection, total=2
        )

        # Then
        assert len(response.data) == 2
        assert response.data[0].type == "source_websites"
        assert response.data[0].id == "1"
        assert response.data[1].id == "2"

    def test_handle_collection_success_should_include_meta_total(
        self, sample_store_collection
    ):
        """
        Given: A collection with a known total
        When: StorePresenter.handle_collection_success() is called
        Then: Should include meta with total count
        """
        # When
        response = StorePresenter.handle_collection_success(
            sample_store_collection, total=100
        )

        # Then
        assert response.meta == {"total": 100}

    def test_handle_collection_success_should_handle_empty_collection(self):
        """
        Given: An empty list
        When: StorePresenter.handle_collection_success() is called
        Then: Should return empty data list with total=0
        """
        # When
        response = StorePresenter.handle_collection_success([], total=0)

        # Then
        assert response.data == []
        assert response.meta == {"total": 0}


# ============================================================================
# StorePresenter.handle_validation_errors Tests
# ============================================================================


class TestStorePresenterHandleValidationErrors:
    """Tests for StorePresenter.handle_validation_errors()."""

    def test_handle_validation_errors_should_return_jsonapi_error_response(
        self, sample_validation_errors
    ):
        """
        Given: A list of validation errors
        When: StorePresenter.handle_validation_errors() is called
        Then: Should return JSONResponse with correct JSON:API error structure
        """
        # When
        response = StorePresenter.handle_validation_errors(sample_validation_errors)

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        assert response.media_type == "application/vnd.api+json"

    def test_handle_validation_errors_should_include_all_errors(
        self, sample_validation_errors
    ):
        """
        Given: Multiple validation errors
        When: StorePresenter.handle_validation_errors() is called
        Then: Should include all errors in the response body
        """
        # When
        response = StorePresenter.handle_validation_errors(sample_validation_errors)
        content = response.body.decode("utf-8")

        # Then
        assert "MISSING_FIELD" in content
        assert "INVALID_URL" in content
        assert "name" in content

    def test_handle_validation_errors_should_use_first_error_status_code(self):
        """
        Given: Validation errors starting with status 400
        When: StorePresenter.handle_validation_errors() is called
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
        response = StorePresenter.handle_validation_errors(errors)

        # Then
        assert response.status_code == 400


# ============================================================================
# StorePresenter.handle_not_found Tests
# ============================================================================


class TestStorePresenterHandleNotFound:
    """Tests for StorePresenter.handle_not_found()."""

    def test_handle_not_found_should_return_404_jsonapi_error(self):
        """
        Given: A source website identifier
        When: StorePresenter.handle_not_found() is called
        Then: Should return 404 JSONResponse with JSON:API error structure
        """
        # When
        response = StorePresenter.handle_not_found(
            identifier="id=999", pointer="/data/attributes/id"
        )

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        assert response.media_type == "application/vnd.api+json"

    def test_handle_not_found_should_include_identifier_in_detail(self):
        """
        Given: A specific source website identifier
        When: StorePresenter.handle_not_found() is called
        Then: Should include identifier in the error detail
        """
        # When
        response = StorePresenter.handle_not_found(
            identifier="name='NonExistentSite'",
            pointer="/data/attributes/name",
        )
        content = response.body.decode("utf-8")

        # Then
        assert "NonExistentSite" in content
        assert "NOT_FOUND" in content

    def test_handle_not_found_should_have_correct_error_structure(self):
        """
        Given: A source website identifier
        When: StorePresenter.handle_not_found() is called
        Then: Should have correct JSON:API error fields
        """
        # When
        response = StorePresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"status":"404"' in content or '"status": "404"' in content
        assert '"code":"NOT_FOUND"' in content or '"code": "NOT_FOUND"' in content
        assert (
            '"title":"Source website not found"' in content
            or '"title": "Source website not found"' in content
        )

    def test_handle_not_found_should_use_default_pointer(self):
        """
        Given: No pointer specified
        When: StorePresenter.handle_not_found() is called
        Then: Should use default pointer '/data'
        """
        # When
        response = StorePresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"/data"' in content or "pointer" in content
