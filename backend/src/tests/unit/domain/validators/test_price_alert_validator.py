"""Unit tests for PriceAlertValidator."""

from unittest.mock import Mock

from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.http.price_alert_schema import (
    PriceAlertAttributesForCreation,
    PriceAlertAttributesForUpdate,
    PriceAlertCreateRequest,
    PriceAlertResourceForCreation,
    PriceAlertResourceForUpdate,
    PriceAlertUpdateRequest,
)
from src.app.alerts.rules import PriceAlertValidator

# ============================================================================
# Helpers
# ============================================================================


def make_create_request(**overrides) -> PriceAlertCreateRequest:
    attrs_data = {
        "search_term": overrides.pop("search_term", "iPhone 13"),
        "max_price": overrides.pop("max_price", 2500.00),
        "user_id": overrides.pop("user_id", 1),
        "is_active": overrides.pop("is_active", True),
        "frequency_minutes": overrides.pop("frequency_minutes", 60),
        "source_website_ids": overrides.pop("source_website_ids", []),
        **overrides,
    }
    attrs = PriceAlertAttributesForCreation(**attrs_data)
    return PriceAlertCreateRequest(
        data=PriceAlertResourceForCreation(type="price_alert", attributes=attrs)
    )


def make_update_request(**overrides) -> PriceAlertUpdateRequest:
    attrs = PriceAlertAttributesForUpdate(**overrides)
    return PriceAlertUpdateRequest(
        data=PriceAlertResourceForUpdate(type="price_alert", attributes=attrs)
    )


def make_price_alert_entity(**overrides) -> PriceAlertEntity:
    defaults = {
        "id": 1,
        "search_term": "iPhone 13",
        "max_price": 2500.00,
        "is_active": True,
        "frequency_minutes": 60,
        "user_id": 1,
        "source_website_ids": [],
    }
    defaults.update(overrides)
    return PriceAlertEntity(**defaults)


# ============================================================================
# Tests: validate_create_request
# ============================================================================


class TestPriceAlertValidatorCreate:
    """Tests for PriceAlertValidator.validate_create_request"""

    def test_valid_create_request_returns_no_errors(self):
        """
        Given: A valid create request with required fields and no conflicts
        When: validate_create_request is called
        Then: Returns empty errors list
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()
        mock_pa_repo.get_by_search_term_and_user_id.return_value = None
        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)

        errors = validator.validate_create_request(make_create_request())

        assert errors == []

    def test_create_with_invalid_type_returns_400(self):
        """
        Given: type != 'price_alert'
        When: validate_create_request is called
        Then: Returns 400 INVALID_TYPE error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()
        request = make_create_request()
        request.data.type = "price_alerts"

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_create_request(request)

        assert len(errors) == 1
        assert errors[0].code == "INVALID_TYPE"
        assert errors[0].status == "400"

    def test_create_with_empty_search_term_returns_422(self):
        """
        Given: Empty search_term
        When: validate_create_request is called
        Then: Returns 422 MISSING_FIELD error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_create_request(
            make_create_request(search_term="   ")
        )

        assert len(errors) >= 1
        assert any(e.code == "MISSING_FIELD" for e in errors)

    def test_create_with_negative_max_price_returns_422(self):
        """
        Given: Negative max_price
        When: validate_create_request is called
        Then: Returns 422 INVALID_FIELD error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_create_request(
            make_create_request(max_price=-100.0)
        )

        assert len(errors) >= 1
        assert any(e.code == "INVALID_FIELD" for e in errors)

    def test_create_with_negative_frequency_minutes_returns_422(self):
        """
        Given: Negative frequency_minutes
        When: validate_create_request is called
        Then: Returns 422 INVALID_FIELD error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_create_request(
            make_create_request(frequency_minutes=-10)
        )

        assert len(errors) >= 1
        assert any(e.code == "INVALID_FIELD" for e in errors)

    def test_create_with_nonexistent_source_website_returns_404(self):
        """
        Given: source_website_ids with non-existent id
        When: validate_create_request is called
        Then: Returns 404 SOURCE_WEBSITE_NOT_FOUND error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()
        mock_pa_repo.get_by_search_term_and_user_id.return_value = None
        mock_sw_repo.get_by_id.return_value = None

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_create_request(
            make_create_request(source_website_ids=[999])
        )

        assert len(errors) == 1
        assert errors[0].code == "SOURCE_WEBSITE_NOT_FOUND"

    def test_create_with_duplicate_search_term_returns_409(self):
        """
        Given: search_term already exists for this user
        When: validate_create_request is called
        Then: Returns 409 DUPLICATE_SEARCH_TERM error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()
        mock_pa_repo.get_by_search_term_and_user_id.return_value = (
            make_price_alert_entity()
        )

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_create_request(make_create_request())

        assert len(errors) == 1
        assert errors[0].code == "DUPLICATE_SEARCH_TERM"
        assert errors[0].status == "409"


# ============================================================================
# Tests: validate_update_request
# ============================================================================


class TestPriceAlertValidatorUpdate:
    """Tests for PriceAlertValidator.validate_update_request"""

    def test_valid_update_request_returns_no_errors(self):
        """
        Given: A valid update request
        When: validate_update_request is called
        Then: Returns empty errors list
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()
        mock_pa_repo.get_by_id.return_value = make_price_alert_entity(id=1, user_id=1)
        mock_pa_repo.get_by_search_term_and_user_id.return_value = None
        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)

        errors = validator.validate_update_request(
            1, make_update_request(search_term="iPhone 14")
        )

        assert errors == []

    def test_update_with_invalid_type_returns_400(self):
        """
        Given: type != 'price_alert'
        When: validate_update_request is called
        Then: Returns 400 INVALID_TYPE error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()
        request = make_update_request(search_term="test")
        request.data.type = "price_alerts"

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_update_request(1, request)

        assert len(errors) == 1
        assert errors[0].code == "INVALID_TYPE"

    def test_update_with_empty_search_term_returns_422(self):
        """
        Given: Empty search_term in update
        When: validate_update_request is called
        Then: Returns 422 INVALID_VALUE error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_update_request(
            1, make_update_request(search_term="   ")
        )

        assert len(errors) >= 1
        assert any(e.code == "INVALID_VALUE" for e in errors)

    def test_update_with_negative_max_price_returns_422(self):
        """
        Given: Negative max_price in update
        When: validate_update_request is called
        Then: Returns 422 INVALID_FIELD error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_update_request(
            1, make_update_request(max_price=-50.0)
        )

        assert len(errors) >= 1
        assert any(e.code == "INVALID_FIELD" for e in errors)

    def test_update_with_negative_frequency_minutes_returns_422(self):
        """
        Given: Negative frequency_minutes in update
        When: validate_update_request is called
        Then: Returns 422 INVALID_FIELD error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_update_request(
            1, make_update_request(frequency_minutes=-5)
        )

        assert len(errors) >= 1
        assert any(e.code == "INVALID_FIELD" for e in errors)

    def test_update_with_duplicate_search_term_returns_409(self):
        """
        Given: search_term already taken by another alert for same user
        When: validate_update_request is called
        Then: Returns 409 DUPLICATE_SEARCH_TERM error
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()
        mock_pa_repo.get_by_id.return_value = make_price_alert_entity(id=1, user_id=1)
        mock_pa_repo.get_by_search_term_and_user_id.return_value = (
            make_price_alert_entity(id=2, search_term="iPhone 14", user_id=1)
        )

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_update_request(
            1, make_update_request(search_term="iPhone 14")
        )

        assert len(errors) == 1
        assert errors[0].code == "DUPLICATE_SEARCH_TERM"

    def test_update_same_search_term_on_same_alert_returns_no_errors(self):
        """
        Given: search_term matches the same alert being updated
        When: validate_update_request is called
        Then: Returns empty errors list (not a conflict)
        """
        mock_pa_repo = Mock()
        mock_sw_repo = Mock()
        entity = make_price_alert_entity(id=1, search_term="iPhone 13", user_id=1)
        mock_pa_repo.get_by_id.return_value = entity
        mock_pa_repo.get_by_search_term_and_user_id.return_value = entity

        validator = PriceAlertValidator(mock_pa_repo, mock_sw_repo)
        errors = validator.validate_update_request(
            1, make_update_request(search_term="iPhone 13")
        )

        assert errors == []
