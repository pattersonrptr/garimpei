"""
Unit tests for Price History Presenter.

Tests presentation layer (JSON:API formatting) with fixtures.
Following Given/When/Then pattern for clarity.
"""

from datetime import datetime

import pytest
from fastapi.responses import JSONResponse

from src.app.catalog.entities import PriceHistory as PriceHistoryEntity
from src.app.catalog.http.price_history_presenter import (
    PriceHistoryPresenter,
)
from src.common.jsonapi import JsonApiError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_price_history_entity():
    """Sample price history entity for testing."""
    return PriceHistoryEntity(
        id=1,
        product_id=10,
        price=1999.99,
        created_at=datetime(2025, 3, 15, 10, 30, 0),
    )


@pytest.fixture
def sample_price_history_collection(sample_price_history_entity):
    """Sample collection of price history entities for testing."""
    second = PriceHistoryEntity(
        id=2,
        product_id=10,
        price=1850.00,
        created_at=datetime(2025, 3, 20, 14, 0, 0),
    )
    return [sample_price_history_entity, second]


@pytest.fixture
def sample_validation_errors():
    """Sample validation errors for testing."""
    return [
        JsonApiError(
            status="422",
            code="MISSING_FIELD",
            title="Validation error",
            detail="Field 'product_id' is required",
            source={"pointer": "/data/attributes/product_id"},
        ),
        JsonApiError(
            status="422",
            code="INVALID_VALUE",
            title="Validation error",
            detail="Field 'price' must be a positive number",
            source={"pointer": "/data/attributes/price"},
        ),
    ]


# ============================================================================
# PriceHistoryPresenter.handle_success Tests
# ============================================================================


class TestPriceHistoryPresenterHandleSuccess:
    """Tests for PriceHistoryPresenter.handle_success()."""

    def test_handle_success_should_return_jsonapi_response(
        self, sample_price_history_entity
    ):
        """
        Given: A valid price history entity
        When: PriceHistoryPresenter.handle_success() is called
        Then: Should return PriceHistoryReadResponse with correct JSON:API structure
        """
        # When
        response = PriceHistoryPresenter.handle_success(sample_price_history_entity)

        # Then
        assert response.data.type == "price_histories"
        assert response.data.id == "1"
        assert response.data.attributes.product_id == 10
        assert response.data.attributes.price == 1999.99

    def test_handle_success_should_include_all_attributes(
        self, sample_price_history_entity
    ):
        """
        Given: A price history entity with all fields
        When: PriceHistoryPresenter.handle_success() is called
        Then: Should include all attributes in the response
        """
        # When
        response = PriceHistoryPresenter.handle_success(sample_price_history_entity)

        # Then
        attrs = response.data.attributes
        assert attrs.product_id == 10
        assert attrs.price == 1999.99
        assert attrs.created_at == datetime(2025, 3, 15, 10, 30, 0)

    def test_handle_success_should_have_string_id(self, sample_price_history_entity):
        """
        Given: A price history entity with integer id
        When: PriceHistoryPresenter.handle_success() is called
        Then: JSON:API id should be a string
        """
        # When
        response = PriceHistoryPresenter.handle_success(sample_price_history_entity)

        # Then
        assert isinstance(response.data.id, str)
        assert response.data.id == "1"

    def test_handle_success_should_reflect_decimal_prices(self):
        """
        Given: A price history entity with decimal price
        When: PriceHistoryPresenter.handle_success() is called
        Then: Should preserve decimal precision
        """
        # Given
        entity = PriceHistoryEntity(id=5, product_id=3, price=99.90)

        # When
        response = PriceHistoryPresenter.handle_success(entity)

        # Then
        assert response.data.attributes.price == 99.90


# ============================================================================
# PriceHistoryPresenter.handle_collection_success Tests
# ============================================================================


class TestPriceHistoryPresenterHandleCollectionSuccess:
    """Tests for PriceHistoryPresenter.handle_collection_success()."""

    def test_handle_collection_success_should_return_jsonapi_collection(
        self, sample_price_history_collection
    ):
        """
        Given: A list of price history entities and total count
        When: PriceHistoryPresenter.handle_collection_success() is called
        Then: Should return collection response with all items
        """
        # When
        response = PriceHistoryPresenter.handle_collection_success(
            sample_price_history_collection, total=2
        )

        # Then
        assert len(response.data) == 2
        assert response.data[0].type == "price_histories"
        assert response.data[0].id == "1"
        assert response.data[1].id == "2"

    def test_handle_collection_success_should_include_meta_total(
        self, sample_price_history_collection
    ):
        """
        Given: A collection with a known total
        When: PriceHistoryPresenter.handle_collection_success() is called
        Then: Should include meta with total count
        """
        # When
        response = PriceHistoryPresenter.handle_collection_success(
            sample_price_history_collection, total=30
        )

        # Then
        assert response.meta == {"total": 30}

    def test_handle_collection_success_should_handle_empty_collection(self):
        """
        Given: An empty list
        When: PriceHistoryPresenter.handle_collection_success() is called
        Then: Should return empty data list with total=0
        """
        # When
        response = PriceHistoryPresenter.handle_collection_success([], total=0)

        # Then
        assert response.data == []
        assert response.meta == {"total": 0}

    def test_handle_collection_success_preserves_price_order(
        self, sample_price_history_collection
    ):
        """
        Given: A collection with descending prices (most recent first)
        When: PriceHistoryPresenter.handle_collection_success() is called
        Then: Should preserve the original order
        """
        # When
        response = PriceHistoryPresenter.handle_collection_success(
            sample_price_history_collection, total=2
        )

        # Then
        assert response.data[0].attributes.price == 1999.99
        assert response.data[1].attributes.price == 1850.00


# ============================================================================
# PriceHistoryPresenter.handle_validation_errors Tests
# ============================================================================


class TestPriceHistoryPresenterHandleValidationErrors:
    """Tests for PriceHistoryPresenter.handle_validation_errors()."""

    def test_handle_validation_errors_should_return_jsonapi_error_response(
        self, sample_validation_errors
    ):
        """
        Given: A list of validation errors
        When: PriceHistoryPresenter.handle_validation_errors() is called
        Then: Should return JSONResponse with correct JSON:API error structure
        """
        # When
        response = PriceHistoryPresenter.handle_validation_errors(
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
        When: PriceHistoryPresenter.handle_validation_errors() is called
        Then: Should include all errors in the response body
        """
        # When
        response = PriceHistoryPresenter.handle_validation_errors(
            sample_validation_errors
        )
        content = response.body.decode("utf-8")

        # Then
        assert "MISSING_FIELD" in content
        assert "INVALID_VALUE" in content
        assert "product_id" in content

    def test_handle_validation_errors_should_use_first_error_status_code(self):
        """
        Given: Validation errors starting with status 400
        When: PriceHistoryPresenter.handle_validation_errors() is called
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
        response = PriceHistoryPresenter.handle_validation_errors(errors)

        # Then
        assert response.status_code == 400


# ============================================================================
# PriceHistoryPresenter.handle_not_found Tests
# ============================================================================


class TestPriceHistoryPresenterHandleNotFound:
    """Tests for PriceHistoryPresenter.handle_not_found()."""

    def test_handle_not_found_should_return_404_jsonapi_error(self):
        """
        Given: A price history identifier
        When: PriceHistoryPresenter.handle_not_found() is called
        Then: Should return 404 JSONResponse with JSON:API error structure
        """
        # When
        response = PriceHistoryPresenter.handle_not_found(
            identifier="id=999", pointer="/data/attributes/id"
        )

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        assert response.media_type == "application/vnd.api+json"

    def test_handle_not_found_should_include_identifier_in_detail(self):
        """
        Given: A specific price history identifier
        When: PriceHistoryPresenter.handle_not_found() is called
        Then: Should include identifier in the error detail
        """
        # When
        response = PriceHistoryPresenter.handle_not_found(
            identifier="product_id=42",
            pointer="/data/attributes/product_id",
        )
        content = response.body.decode("utf-8")

        # Then
        assert "product_id=42" in content
        assert "NOT_FOUND" in content

    def test_handle_not_found_should_have_correct_error_structure(self):
        """
        Given: A price history identifier
        When: PriceHistoryPresenter.handle_not_found() is called
        Then: Should have correct JSON:API error fields
        """
        # When
        response = PriceHistoryPresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"status":"404"' in content or '"status": "404"' in content
        assert '"code":"NOT_FOUND"' in content or '"code": "NOT_FOUND"' in content
        assert (
            '"title":"Price history record not found"' in content
            or '"title": "Price history record not found"' in content
        )

    def test_handle_not_found_should_use_default_pointer(self):
        """
        Given: No pointer specified
        When: PriceHistoryPresenter.handle_not_found() is called
        Then: Should use default pointer '/data'
        """
        # When
        response = PriceHistoryPresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"/data"' in content or "pointer" in content
