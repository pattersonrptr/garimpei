"""Unit tests for ProductValidator."""

from unittest.mock import Mock

import pytest

from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.entities import ProductCondition
from src.app.catalog.http.product_schema import (
    ProductAttributesForCreation,
    ProductAttributesForUpdate,
    ProductCreateRequest,
    ProductResourceForCreation,
    ProductResourceForUpdate,
    ProductUpdateRequest,
)
from src.app.catalog.rules import ProductValidator

# ============================================================================
# Helpers
# ============================================================================


def make_create_request(**overrides) -> ProductCreateRequest:
    defaults = {
        "url": "https://www.olx.com.br/item/test-product",
        "title": "Test Product",
        "source_website_id": 1,
    }
    defaults.update(overrides)
    return ProductCreateRequest(
        data=ProductResourceForCreation(
            type="product",
            attributes=ProductAttributesForCreation(**defaults),
        )
    )


def make_update_request(**overrides) -> ProductUpdateRequest:
    return ProductUpdateRequest(
        data=ProductResourceForUpdate(
            type="product",
            attributes=ProductAttributesForUpdate(**overrides),
        )
    )


def make_product_entity(**overrides) -> ProductEntity:
    defaults = {
        "id": 1,
        "url": "https://www.olx.com.br/item/existing-product",
        "title": "Existing Product",
        "source_website_id": 1,
        "condition": ProductCondition.USED,
        "is_available": True,
    }
    defaults.update(overrides)
    return ProductEntity(**defaults)


# ============================================================================
# TestProductValidatorCreate
# ============================================================================


class TestProductValidatorCreate:
    """Tests for validate_create_request method."""

    def test_valid_create_request_should_return_no_errors(self):
        """
        Given: A valid product creation request with unique URL
        When: validate_create_request is called
        Then: Should return an empty list of errors
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_url.return_value = None
        validator = ProductValidator(mock_repo)

        request = make_create_request()

        # Act
        errors = validator.validate_create_request(request)

        # Assert
        assert errors == []
        mock_repo.get_by_url.assert_called_once_with(
            "https://www.olx.com.br/item/test-product"
        )

    def test_create_request_with_invalid_type_should_return_error(self):
        """
        Given: A creation request with wrong JSON:API type
        When: validate_create_request is called
        Then: Should return INVALID_TYPE error and not check for duplicates
        """
        # Arrange
        mock_repo = Mock()
        validator = ProductValidator(mock_repo)

        request = ProductCreateRequest(
            data=ProductResourceForCreation(
                type="wrong_type",
                attributes=ProductAttributesForCreation(
                    url="https://www.olx.com.br/item/test",
                    title="Test",
                    source_website_id=1,
                ),
            )
        )

        # Act
        errors = validator.validate_create_request(request)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "INVALID_TYPE"
        assert errors[0].status == "400"
        assert errors[0].source["pointer"] == "/data/type"
        assert "wrong_type" in errors[0].detail
        mock_repo.get_by_url.assert_not_called()

    @pytest.mark.parametrize(
        "field,value",
        [
            ("url", ""),
            ("title", ""),
        ],
        ids=["empty_url", "empty_title"],
    )
    def test_create_request_with_empty_required_field_should_return_error(
        self, field, value
    ):
        """
        Given: A creation request with an empty required field
        When: validate_create_request is called
        Then: Should return MISSING_FIELD error and not check for duplicates
        """
        # Arrange
        mock_repo = Mock()
        validator = ProductValidator(mock_repo)

        request = make_create_request(**{field: value})

        # Act
        errors = validator.validate_create_request(request)

        # Assert
        assert len(errors) >= 1
        codes = [e.code for e in errors]
        assert "MISSING_FIELD" in codes
        pointer = f"/data/attributes/{field}"
        assert any(e.source["pointer"] == pointer for e in errors)
        mock_repo.get_by_url.assert_not_called()

    def test_create_request_with_duplicate_url_should_return_conflict_error(self):
        """
        Given: A creation request with a URL that already exists
        When: validate_create_request is called
        Then: Should return DUPLICATE_URL error with status 409
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_url.return_value = make_product_entity(
            url="https://www.olx.com.br/item/test-product"
        )
        validator = ProductValidator(mock_repo)

        request = make_create_request(url="https://www.olx.com.br/item/test-product")

        # Act
        errors = validator.validate_create_request(request)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "DUPLICATE_URL"
        assert errors[0].status == "409"
        assert errors[0].source["pointer"] == "/data/attributes/url"
        assert "https://www.olx.com.br/item/test-product" in errors[0].detail

    def test_create_request_with_multiple_missing_fields_should_return_all_errors(
        self,
    ):
        """
        Given: A creation request with multiple empty required fields
        When: validate_create_request is called
        Then: Should return errors for all missing fields (early return before duplicate check)
        """
        # Arrange
        mock_repo = Mock()
        validator = ProductValidator(mock_repo)

        request = make_create_request(url="", title="")

        # Act
        errors = validator.validate_create_request(request)

        # Assert
        assert len(errors) >= 2
        codes = [e.code for e in errors]
        assert codes.count("MISSING_FIELD") == 2
        mock_repo.get_by_url.assert_not_called()


# ============================================================================
# TestProductValidatorUpdate
# ============================================================================


class TestProductValidatorUpdate:
    """Tests for validate_update_request method."""

    def test_valid_update_request_should_return_no_errors(self):
        """
        Given: A valid update request with unique URL
        When: validate_update_request is called
        Then: Should return empty list of errors
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_url.return_value = None
        validator = ProductValidator(mock_repo)

        request = make_update_request(
            title="Updated Title",
            url="https://www.olx.com.br/item/new-unique-url",
        )

        # Act
        errors = validator.validate_update_request(1, request)

        # Assert
        assert errors == []

    def test_valid_update_with_no_url_should_not_check_duplicates(self):
        """
        Given: An update request that does not change the URL
        When: validate_update_request is called
        Then: Should not check for URL duplicates
        """
        # Arrange
        mock_repo = Mock()
        validator = ProductValidator(mock_repo)

        request = make_update_request(title="New Title")

        # Act
        errors = validator.validate_update_request(1, request)

        # Assert
        assert errors == []
        mock_repo.get_by_url.assert_not_called()

    def test_update_request_with_invalid_type_should_return_error(self):
        """
        Given: An update request with wrong JSON:API type
        When: validate_update_request is called
        Then: Should return INVALID_TYPE error
        """
        # Arrange
        mock_repo = Mock()
        validator = ProductValidator(mock_repo)

        request = ProductUpdateRequest(
            data=ProductResourceForUpdate(
                type="wrong_type",
                attributes=ProductAttributesForUpdate(title="New Title"),
            )
        )

        # Act
        errors = validator.validate_update_request(1, request)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "INVALID_TYPE"
        assert errors[0].status == "400"
        assert errors[0].source["pointer"] == "/data/type"

    def test_update_request_with_empty_title_should_return_error(self):
        """
        Given: An update request with empty title string
        When: validate_update_request is called
        Then: Should return INVALID_VALUE error
        """
        # Arrange
        mock_repo = Mock()
        validator = ProductValidator(mock_repo)

        request = make_update_request(title="")

        # Act
        errors = validator.validate_update_request(1, request)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "INVALID_VALUE"
        assert errors[0].status == "422"
        assert errors[0].source["pointer"] == "/data/attributes/title"

    def test_update_request_with_empty_url_should_return_error(self):
        """
        Given: An update request with empty URL string
        When: validate_update_request is called
        Then: Should return INVALID_VALUE error
        """
        # Arrange
        mock_repo = Mock()
        validator = ProductValidator(mock_repo)

        request = make_update_request(url="")

        # Act
        errors = validator.validate_update_request(1, request)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "INVALID_VALUE"
        assert errors[0].status == "422"
        assert errors[0].source["pointer"] == "/data/attributes/url"

    def test_update_request_with_url_from_another_product_should_return_conflict(self):
        """
        Given: An update request with a URL belonging to a different product
        When: validate_update_request is called
        Then: Should return DUPLICATE_URL error with status 409
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_url.return_value = make_product_entity(
            id=99,
            url="https://www.olx.com.br/item/other-product",
        )
        validator = ProductValidator(mock_repo)

        request = make_update_request(url="https://www.olx.com.br/item/other-product")

        # Act
        errors = validator.validate_update_request(1, request)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "DUPLICATE_URL"
        assert errors[0].status == "409"
        assert errors[0].source["pointer"] == "/data/attributes/url"

    def test_update_request_with_own_url_should_return_no_errors(self):
        """
        Given: An update request using the same product's own URL
        When: validate_update_request is called
        Then: Should return no errors (keeping the same URL is allowed)
        """
        # Arrange
        mock_repo = Mock()
        mock_repo.get_by_url.return_value = make_product_entity(
            id=1,
            url="https://www.olx.com.br/item/same-product",
        )
        validator = ProductValidator(mock_repo)

        request = make_update_request(url="https://www.olx.com.br/item/same-product")

        # Act
        errors = validator.validate_update_request(1, request)

        # Assert
        assert errors == []
