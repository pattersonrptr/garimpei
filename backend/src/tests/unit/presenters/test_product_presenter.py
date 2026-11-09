"""
Unit tests for Product Presenter.

Tests presentation layer (JSON:API formatting) with fixtures.
Following Given/When/Then pattern for clarity.
"""

from datetime import datetime

import pytest
from fastapi.responses import JSONResponse

from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.http.product_presenter import ProductPresenter
from src.common.jsonapi import JsonApiError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_product_entity():
    """Sample product entity for testing."""
    return ProductEntity(
        id=1,
        url="https://www.mercadolivre.com.br/notebook-lenovo",
        title="Notebook Lenovo ThinkPad",
        source_product_code="MLB-123456",
        description="Notebook em ótimo estado",
        condition="new",
        seller_name="Loja Oficial",
        is_available=True,
        source_website_id=1,
        source_metadata={"category": "notebooks"},
        current_price=3999.99,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_product_collection(sample_product_entity):
    """Sample collection of product entities for testing."""
    second = ProductEntity(
        id=2,
        url="https://www.mercadolivre.com.br/notebook-dell",
        title="Notebook Dell Inspiron",
        source_product_code="MLB-654321",
        condition="used",
        seller_name="Vendedor XYZ",
        is_available=True,
        source_website_id=1,
        created_at=datetime(2025, 1, 2, 12, 0, 0),
        updated_at=datetime(2025, 1, 2, 12, 0, 0),
    )
    return [sample_product_entity, second]


@pytest.fixture
def sample_validation_errors():
    """Sample validation errors for testing."""
    return [
        JsonApiError(
            status="422",
            code="MISSING_FIELD",
            title="Validation error",
            detail="Field 'url' is required",
            source={"pointer": "/data/attributes/url"},
        ),
        JsonApiError(
            status="422",
            code="INVALID_FORMAT",
            title="Validation error",
            detail="Field 'url' must be a valid URL",
            source={"pointer": "/data/attributes/url"},
        ),
    ]


# ============================================================================
# ProductPresenter.handle_success Tests
# ============================================================================


class TestProductPresenterHandleSuccess:
    """Tests for ProductPresenter.handle_success()."""

    def test_handle_success_should_return_jsonapi_response(self, sample_product_entity):
        """
        Given: A valid product entity
        When: ProductPresenter.handle_success() is called
        Then: Should return ProductReadResponse with correct JSON:API structure
        """
        # When
        response = ProductPresenter.handle_success(sample_product_entity)

        # Then
        assert response.data.type == "products"
        assert response.data.id == "1"
        assert (
            response.data.attributes.url
            == "https://www.mercadolivre.com.br/notebook-lenovo"
        )
        assert response.data.attributes.title == "Notebook Lenovo ThinkPad"

    def test_handle_success_should_include_all_attributes(self, sample_product_entity):
        """
        Given: A product entity with all fields
        When: ProductPresenter.handle_success() is called
        Then: Should include all attributes in the response
        """
        # When
        response = ProductPresenter.handle_success(sample_product_entity)

        # Then
        attrs = response.data.attributes
        assert attrs.source_product_code == "MLB-123456"
        assert attrs.description == "Notebook em ótimo estado"
        assert attrs.seller_name == "Loja Oficial"
        assert attrs.is_available is True
        assert attrs.source_website_id == 1
        assert attrs.current_price == 3999.99

    def test_handle_success_should_include_timestamps(self, sample_product_entity):
        """
        Given: A product entity with timestamps
        When: ProductPresenter.handle_success() is called
        Then: Should include created_at and updated_at in attributes
        """
        # When
        response = ProductPresenter.handle_success(sample_product_entity)

        # Then
        assert response.data.attributes.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert response.data.attributes.updated_at == datetime(2025, 1, 1, 12, 0, 0)

    def test_handle_success_should_have_string_id(self, sample_product_entity):
        """
        Given: A product entity with integer id
        When: ProductPresenter.handle_success() is called
        Then: JSON:API id should be a string
        """
        # When
        response = ProductPresenter.handle_success(sample_product_entity)

        # Then
        assert isinstance(response.data.id, str)
        assert response.data.id == "1"


# ============================================================================
# ProductPresenter.handle_collection_success Tests
# ============================================================================


class TestProductPresenterHandleCollectionSuccess:
    """Tests for ProductPresenter.handle_collection_success()."""

    def test_handle_collection_success_should_return_jsonapi_collection(
        self, sample_product_collection
    ):
        """
        Given: A list of product entities and total count
        When: ProductPresenter.handle_collection_success() is called
        Then: Should return ProductsCollectionResponse with all items
        """
        # When
        response = ProductPresenter.handle_collection_success(
            sample_product_collection, total=2
        )

        # Then
        assert len(response.data) == 2
        assert response.data[0].type == "products"
        assert response.data[0].id == "1"
        assert response.data[1].id == "2"

    def test_handle_collection_success_should_include_meta_total(
        self, sample_product_collection
    ):
        """
        Given: A collection with a known total
        When: ProductPresenter.handle_collection_success() is called
        Then: Should include meta with total count
        """
        # When
        response = ProductPresenter.handle_collection_success(
            sample_product_collection, total=50
        )

        # Then
        assert response.meta == {"total": 50}

    def test_handle_collection_success_should_handle_empty_collection(self):
        """
        Given: An empty list
        When: ProductPresenter.handle_collection_success() is called
        Then: Should return empty data list with total=0
        """
        # When
        response = ProductPresenter.handle_collection_success([], total=0)

        # Then
        assert response.data == []
        assert response.meta == {"total": 0}


# ============================================================================
# ProductPresenter.handle_validation_errors Tests
# ============================================================================


class TestProductPresenterHandleValidationErrors:
    """Tests for ProductPresenter.handle_validation_errors()."""

    def test_handle_validation_errors_should_return_jsonapi_error_response(
        self, sample_validation_errors
    ):
        """
        Given: A list of validation errors
        When: ProductPresenter.handle_validation_errors() is called
        Then: Should return JSONResponse with correct JSON:API error structure
        """
        # When
        response = ProductPresenter.handle_validation_errors(sample_validation_errors)

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        assert response.media_type == "application/vnd.api+json"

    def test_handle_validation_errors_should_include_all_errors(
        self, sample_validation_errors
    ):
        """
        Given: Multiple validation errors
        When: ProductPresenter.handle_validation_errors() is called
        Then: Should include all errors in the response body
        """
        # When
        response = ProductPresenter.handle_validation_errors(sample_validation_errors)
        content = response.body.decode("utf-8")

        # Then
        assert "MISSING_FIELD" in content
        assert "INVALID_FORMAT" in content
        assert "url" in content

    def test_handle_validation_errors_should_use_first_error_status_code(self):
        """
        Given: Validation errors starting with status 400
        When: ProductPresenter.handle_validation_errors() is called
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
        response = ProductPresenter.handle_validation_errors(errors)

        # Then
        assert response.status_code == 400


# ============================================================================
# ProductPresenter.handle_not_found Tests
# ============================================================================


class TestProductPresenterHandleNotFound:
    """Tests for ProductPresenter.handle_not_found()."""

    def test_handle_not_found_should_return_404_jsonapi_error(self):
        """
        Given: A product identifier
        When: ProductPresenter.handle_not_found() is called
        Then: Should return 404 JSONResponse with JSON:API error structure
        """
        # When
        response = ProductPresenter.handle_not_found(
            identifier="id=999", pointer="/data/attributes/id"
        )

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        assert response.media_type == "application/vnd.api+json"

    def test_handle_not_found_should_include_identifier_in_detail(self):
        """
        Given: A specific product identifier
        When: ProductPresenter.handle_not_found() is called
        Then: Should include identifier in the error detail
        """
        # When
        response = ProductPresenter.handle_not_found(
            identifier="url='https://example.com/product'",
            pointer="/data/attributes/url",
        )
        content = response.body.decode("utf-8")

        # Then
        assert "example.com/product" in content
        assert "NOT_FOUND" in content

    def test_handle_not_found_should_have_correct_error_structure(self):
        """
        Given: A product identifier
        When: ProductPresenter.handle_not_found() is called
        Then: Should have correct JSON:API error fields
        """
        # When
        response = ProductPresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"status":"404"' in content or '"status": "404"' in content
        assert '"code":"NOT_FOUND"' in content or '"code": "NOT_FOUND"' in content
        assert (
            '"title":"Product not found"' in content
            or '"title": "Product not found"' in content
        )

    def test_handle_not_found_should_use_default_pointer(self):
        """
        Given: No pointer specified
        When: ProductPresenter.handle_not_found() is called
        Then: Should use default pointer '/data'
        """
        # When
        response = ProductPresenter.handle_not_found(identifier="id=1")
        content = response.body.decode("utf-8")

        # Then
        assert '"/data"' in content or "pointer" in content


# ============================================================================
# ProductPresenter.handle_conflict Tests
# ============================================================================


class TestProductPresenterHandleConflict:
    """Tests for ProductPresenter.handle_conflict()."""

    def test_handle_conflict_should_return_409_jsonapi_error(self):
        """
        Given: A conflict detail message
        When: ProductPresenter.handle_conflict() is called
        Then: Should return 409 JSONResponse with JSON:API error structure
        """
        # When
        response = ProductPresenter.handle_conflict(
            detail="Product with this URL already exists"
        )

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 409
        assert response.media_type == "application/vnd.api+json"

    def test_handle_conflict_should_include_detail_in_response(self):
        """
        Given: A specific conflict detail
        When: ProductPresenter.handle_conflict() is called
        Then: Should include the detail message in the error response
        """
        # Given
        detail = "Product with URL 'https://example.com' already exists"

        # When
        response = ProductPresenter.handle_conflict(detail=detail)
        content = response.body.decode("utf-8")

        # Then
        assert "example.com" in content
        assert "CONFLICT" in content

    def test_handle_conflict_should_have_correct_error_structure(self):
        """
        Given: A conflict scenario
        When: ProductPresenter.handle_conflict() is called
        Then: Should have correct JSON:API error fields
        """
        # When
        response = ProductPresenter.handle_conflict(detail="Duplicate URL")
        content = response.body.decode("utf-8")

        # Then
        assert '"status":"409"' in content or '"status": "409"' in content
        assert '"code":"CONFLICT"' in content or '"code": "CONFLICT"' in content
        assert (
            '"title":"Resource conflict"' in content
            or '"title": "Resource conflict"' in content
        )
        assert '"/data/attributes/url"' in content
