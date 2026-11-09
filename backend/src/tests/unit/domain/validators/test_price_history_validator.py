"""Unit tests for PriceHistoryValidator."""

from unittest.mock import Mock

import pytest

from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.http.price_history_schema import (
    PriceHistoryAttributesForCreation,
    PriceHistoryCreateRequest,
    PriceHistoryResourceForCreation,
)
from src.app.catalog.rules import PriceHistoryValidator

# ============================================================================
# Helpers
# ============================================================================


def make_create_request(**overrides) -> PriceHistoryCreateRequest:
    attrs = {"product_id": 1, "price": 99.90, **overrides}
    return PriceHistoryCreateRequest(
        data=PriceHistoryResourceForCreation(
            type="price_history",
            attributes=PriceHistoryAttributesForCreation(**attrs),
        )
    )


def make_product_entity(id: int = 1) -> ProductEntity:
    from src.app.catalog.entities import ProductCondition

    return ProductEntity(
        id=id,
        url="https://example.com/product/1",
        title="Test Product",
        condition=ProductCondition.USED,
        source_website_id=1,
    )


# ============================================================================
# Tests
# ============================================================================


class TestPriceHistoryValidatorCreate:
    """Tests for PriceHistoryValidator.validate_create_request"""

    def test_valid_create_request_should_return_no_errors(self):
        """
        Given: A valid create request with product_id=1 and price=99.90
        When: validate_create_request is called
        Then: Returns empty list (no errors)
        """
        price_history_repo = Mock()
        product_repo = Mock()
        product_repo.get_by_id.return_value = make_product_entity()

        validator = PriceHistoryValidator(price_history_repo, product_repo)
        errors = validator.validate_create_request(make_create_request())

        assert errors == []

    def test_create_request_with_invalid_type_should_return_error(self):
        """
        Given: Request with type='price_histories' (plural, wrong)
        When: validate_create_request is called
        Then: Returns one error with status '400' and code 'INVALID_TYPE'
        """
        price_history_repo = Mock()
        product_repo = Mock()

        validator = PriceHistoryValidator(price_history_repo, product_repo)

        request = PriceHistoryCreateRequest(
            data=PriceHistoryResourceForCreation(
                type="price_histories",
                attributes=PriceHistoryAttributesForCreation(product_id=1, price=99.90),
            )
        )
        errors = validator.validate_create_request(request)

        assert len(errors) == 1
        assert errors[0].status == "400"
        assert errors[0].code == "INVALID_TYPE"

    @pytest.mark.parametrize(
        "price",
        [0, -1.0, -0.01],
    )
    def test_create_request_with_invalid_price_should_return_error(self, price):
        """
        Given: Request with price <= 0
        When: validate_create_request is called
        Then: Returns one error with code 'INVALID_FIELD'
        """
        price_history_repo = Mock()
        product_repo = Mock()

        validator = PriceHistoryValidator(price_history_repo, product_repo)
        errors = validator.validate_create_request(make_create_request(price=price))

        assert any(e.code == "INVALID_FIELD" for e in errors)

    @pytest.mark.parametrize("product_id", [0, -1])
    def test_create_request_with_invalid_product_id_should_return_error(
        self, product_id
    ):
        """
        Given: Request with product_id <= 0
        When: validate_create_request is called
        Then: Returns error with code 'MISSING_FIELD'
        """
        price_history_repo = Mock()
        product_repo = Mock()

        validator = PriceHistoryValidator(price_history_repo, product_repo)
        errors = validator.validate_create_request(
            make_create_request(product_id=product_id)
        )

        assert any(e.code == "MISSING_FIELD" for e in errors)

    def test_create_request_with_nonexistent_product_should_return_404_error(self):
        """
        Given: product_id references a product that does not exist
        When: validate_create_request is called
        Then: Returns one error with status '404' and code 'PRODUCT_NOT_FOUND'
        """
        price_history_repo = Mock()
        product_repo = Mock()
        product_repo.get_by_id.return_value = None

        validator = PriceHistoryValidator(price_history_repo, product_repo)
        errors = validator.validate_create_request(make_create_request(product_id=999))

        assert len(errors) == 1
        assert errors[0].status == "404"
        assert errors[0].code == "PRODUCT_NOT_FOUND"

    def test_create_request_with_both_invalid_fields_returns_multiple_errors(self):
        """
        Given: Request with product_id=0 and price=0
        When: validate_create_request is called
        Then: Returns two errors (one per field) — product existence not checked
        """
        price_history_repo = Mock()
        product_repo = Mock()

        validator = PriceHistoryValidator(price_history_repo, product_repo)
        errors = validator.validate_create_request(
            make_create_request(product_id=0, price=0)
        )

        assert len(errors) == 2
        # Product existence check must NOT be called when field errors exist
        product_repo.get_by_id.assert_not_called()
