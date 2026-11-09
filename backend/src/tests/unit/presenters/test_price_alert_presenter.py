"""
Unit tests for Price Alert Presenter.

Tests presentation layer (JSON:API formatting) with fixtures.
Following Given/When/Then pattern for clarity.
"""

from datetime import datetime

import pytest
from fastapi.responses import JSONResponse

from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.http.price_alert_presenter import (
    PriceAlertPresenter,
)
from src.common.jsonapi import JsonApiError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_price_alert_entity():
    """Sample price alert entity for testing."""
    return PriceAlertEntity(
        id=1,
        search_term="notebook lenovo",
        max_price=3500.00,
        is_active=True,
        frequency_minutes=60,
        last_triggered_at=None,
        user_id=1,
        source_website_ids=[1, 2],
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_price_alert_collection(sample_price_alert_entity):
    """Sample collection of price alert entities for testing."""
    second = PriceAlertEntity(
        id=2,
        search_term="iphone 15",
        max_price=5000.00,
        is_active=False,
        frequency_minutes=30,
        user_id=1,
        source_website_ids=[],
        created_at=datetime(2025, 1, 2, 12, 0, 0),
        updated_at=datetime(2025, 1, 2, 12, 0, 0),
    )
    return [sample_price_alert_entity, second]


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
            detail="Field 'max_price' must be a positive number",
            source={"pointer": "/data/attributes/max_price"},
        ),
    ]


# ============================================================================
# PriceAlertPresenter.handle_success Tests
# ============================================================================


class TestPriceAlertPresenterHandleSuccess:
    """Tests for PriceAlertPresenter.handle_success()."""

    def test_handle_success_should_return_jsonapi_response(
        self, sample_price_alert_entity
    ):
        """
        Given: A valid price alert entity
        When: PriceAlertPresenter.handle_success() is called
        Then: Should return PriceAlertReadResponse with correct JSON:API structure
        """
        response = PriceAlertPresenter.handle_success(sample_price_alert_entity)

        assert response.data.type == "price_alerts"
        assert response.data.id == "1"
        assert response.data.attributes.search_term == "notebook lenovo"
        assert response.data.attributes.is_active is True

    def test_handle_success_should_include_all_attributes(
        self, sample_price_alert_entity
    ):
        """
        Given: A price alert entity with all fields
        When: PriceAlertPresenter.handle_success() is called
        Then: Should include all attributes in the response
        """
        response = PriceAlertPresenter.handle_success(sample_price_alert_entity)

        attrs = response.data.attributes
        assert attrs.max_price == 3500.00
        assert attrs.frequency_minutes == 60
        assert attrs.user_id == 1
        assert attrs.source_website_ids == [1, 2]
        assert attrs.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert attrs.updated_at == datetime(2025, 1, 1, 12, 0, 0)

    def test_handle_success_should_have_string_id(self, sample_price_alert_entity):
        """
        Given: A price alert entity with integer id
        When: PriceAlertPresenter.handle_success() is called
        Then: JSON:API id should be a string
        """
        response = PriceAlertPresenter.handle_success(sample_price_alert_entity)

        assert isinstance(response.data.id, str)
        assert response.data.id == "1"

    def test_handle_success_should_reflect_inactive_status(self):
        """
        Given: An inactive price alert entity
        When: PriceAlertPresenter.handle_success() is called
        Then: Should correctly reflect is_active=False
        """
        entity = PriceAlertEntity(
            id=5,
            search_term="test",
            max_price=100.00,
            is_active=False,
            frequency_minutes=60,
            user_id=2,
        )

        response = PriceAlertPresenter.handle_success(entity)

        assert response.data.attributes.is_active is False

    def test_handle_success_should_handle_empty_source_website_ids(self):
        """
        Given: A price alert entity with no source websites
        When: PriceAlertPresenter.handle_success() is called
        Then: Should return empty list for source_website_ids
        """
        entity = PriceAlertEntity(
            id=3,
            search_term="test",
            max_price=200.00,
            is_active=True,
            frequency_minutes=60,
            user_id=1,
            source_website_ids=[],
        )

        response = PriceAlertPresenter.handle_success(entity)

        assert response.data.attributes.source_website_ids == []


# ============================================================================
# PriceAlertPresenter.handle_collection_success Tests
# ============================================================================


class TestPriceAlertPresenterHandleCollectionSuccess:
    """Tests for PriceAlertPresenter.handle_collection_success()."""

    def test_handle_collection_success_should_return_jsonapi_collection(
        self, sample_price_alert_collection
    ):
        """
        Given: A list of price alert entities and total count
        When: PriceAlertPresenter.handle_collection_success() is called
        Then: Should return collection response with all items
        """
        response = PriceAlertPresenter.handle_collection_success(
            sample_price_alert_collection, total=2
        )

        assert len(response.data) == 2
        assert response.meta == {"total": 2}

    def test_handle_collection_success_should_have_correct_types(
        self, sample_price_alert_collection
    ):
        """
        Given: A collection of price alert entities
        When: PriceAlertPresenter.handle_collection_success() is called
        Then: All items should have type 'price_alerts'
        """
        response = PriceAlertPresenter.handle_collection_success(
            sample_price_alert_collection, total=2
        )

        for item in response.data:
            assert item.type == "price_alerts"

    def test_handle_collection_success_should_handle_empty_list(self):
        """
        Given: An empty list of entities
        When: PriceAlertPresenter.handle_collection_success() is called
        Then: Should return empty collection with total=0
        """
        response = PriceAlertPresenter.handle_collection_success([], total=0)

        assert response.data == []
        assert response.meta == {"total": 0}


# ============================================================================
# PriceAlertPresenter.handle_not_found Tests
# ============================================================================


class TestPriceAlertPresenterHandleNotFound:
    """Tests for PriceAlertPresenter.handle_not_found()."""

    def test_handle_not_found_should_return_404_jsonresponse(self):
        """
        Given: An identifier for a non-existent price alert
        When: PriceAlertPresenter.handle_not_found() is called
        Then: Should return JSONResponse with status 404
        """
        response = PriceAlertPresenter.handle_not_found("id 999")

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

    def test_handle_not_found_should_have_jsonapi_error_structure(self):
        """
        Given: An identifier
        When: PriceAlertPresenter.handle_not_found() is called
        Then: Should include errors array with NOT_FOUND code
        """
        response = PriceAlertPresenter.handle_not_found("id 42", "/data/id")

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404


# ============================================================================
# PriceAlertPresenter.handle_validation_errors Tests
# ============================================================================


class TestPriceAlertPresenterHandleValidationErrors:
    """Tests for PriceAlertPresenter.handle_validation_errors()."""

    def test_handle_validation_errors_should_return_jsonresponse(
        self, sample_validation_errors
    ):
        """
        Given: A list of validation errors
        When: PriceAlertPresenter.handle_validation_errors() is called
        Then: Should return JSONResponse with first error's status code
        """
        response = PriceAlertPresenter.handle_validation_errors(
            sample_validation_errors
        )

        assert isinstance(response, JSONResponse)
        assert response.status_code == 422

    def test_handle_validation_errors_should_use_first_error_status(self):
        """
        Given: Errors with different statuses
        When: PriceAlertPresenter.handle_validation_errors() is called
        Then: Should use the first error's status as HTTP status code
        """
        errors = [
            JsonApiError(
                status="400",
                code="INVALID_TYPE",
                title="Bad request",
                detail="Wrong type",
                source={"pointer": "/data/type"},
            ),
        ]

        response = PriceAlertPresenter.handle_validation_errors(errors)

        assert response.status_code == 400
