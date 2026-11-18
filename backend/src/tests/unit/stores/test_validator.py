"""Unit tests for StoreValidator."""

from unittest.mock import Mock

import pytest

from src.app.stores.entities import Store
from src.app.stores.http.store_schema import (
    StoreAttributesForCreation,
    StoreAttributesForUpdate,
    StoreCreateRequest,
    StoreResourceForCreation,
    StoreResourceForUpdate,
    StoreUpdateRequest,
)
from src.app.stores.http.validators import StoreValidator

# ============================================================================
# Helpers
# ============================================================================


def make_create_request(**overrides) -> StoreCreateRequest:
    attrs = StoreAttributesForCreation(
        name=overrides.pop("name", "OLX"),
        base_url=overrides.pop("base_url", "https://www.olx.com.br"),
        **overrides,
    )
    return StoreCreateRequest(
        data=StoreResourceForCreation(type="source_website", attributes=attrs)
    )


def make_update_request(**overrides) -> StoreUpdateRequest:
    attrs = StoreAttributesForUpdate(**overrides)
    return StoreUpdateRequest(
        data=StoreResourceForUpdate(type="source_website", attributes=attrs)
    )


def make_source_website_entity(**overrides) -> Store:
    defaults = {
        "id": 1,
        "name": "OLX",
        "base_url": "https://www.olx.com.br",
        "is_active": True,
    }
    defaults.update(overrides)
    return Store(**defaults)


# ============================================================================
# Tests: validate_create_request
# ============================================================================


class TestStoreValidatorCreate:
    """Tests for StoreValidator.validate_create_request"""

    def test_valid_create_request_should_return_no_errors(self):
        """
        Given: A valid create request with name, base_url and no existing record
        When: validate_create_request is called
        Then: Returns empty errors list
        """
        mock_repo = Mock()
        mock_repo.get_by_name.return_value = None
        validator = StoreValidator(mock_repo)

        errors = validator.validate_create_request(make_create_request())

        assert errors == []

    def test_create_request_with_invalid_type_should_return_error(self):
        """
        Given: A create request with type != 'source_website'
        When: validate_create_request is called
        Then: Returns a 400 INVALID_TYPE error
        """
        mock_repo = Mock()
        request = make_create_request()
        request.data.type = "wrong_type"

        validator = StoreValidator(mock_repo)
        errors = validator.validate_create_request(request)

        assert len(errors) == 1
        assert errors[0].code == "INVALID_TYPE"
        assert errors[0].status == "400"

    @pytest.mark.parametrize(
        "field,value",
        [
            ("name", ""),
            ("name", "   "),
            ("base_url", ""),
            ("base_url", "   "),
        ],
    )
    def test_create_request_with_empty_required_field_should_return_error(
        self, field, value
    ):
        """
        Given: A create request with an empty required field
        When: validate_create_request is called
        Then: Returns a 422 MISSING_FIELD error
        """
        mock_repo = Mock()
        validator = StoreValidator(mock_repo)

        errors = validator.validate_create_request(
            make_create_request(**{field: value})
        )

        assert len(errors) == 1
        assert errors[0].code == "MISSING_FIELD"
        assert errors[0].status == "422"
        assert field in errors[0].source["pointer"]

    def test_create_request_with_duplicate_name_should_return_conflict_error(self):
        """
        Given: A source website with the same name already exists
        When: validate_create_request is called
        Then: Returns a 409 DUPLICATE_NAME error
        """
        mock_repo = Mock()
        mock_repo.get_by_name.return_value = make_source_website_entity()
        validator = StoreValidator(mock_repo)

        errors = validator.validate_create_request(make_create_request(name="OLX"))

        assert len(errors) == 1
        assert errors[0].code == "DUPLICATE_NAME"
        assert errors[0].status == "409"

    def test_create_request_with_both_empty_fields_should_return_both_errors(self):
        """
        Given: A create request with both name and base_url empty
        When: validate_create_request is called
        Then: Returns two MISSING_FIELD errors
        """
        mock_repo = Mock()
        validator = StoreValidator(mock_repo)

        errors = validator.validate_create_request(
            make_create_request(name="", base_url="")
        )

        assert len(errors) == 2
        assert all(e.code == "MISSING_FIELD" for e in errors)


# ============================================================================
# Tests: validate_update_request
# ============================================================================


class TestStoreValidatorUpdate:
    """Tests for StoreValidator.validate_update_request"""

    def test_valid_update_request_should_return_no_errors(self):
        """
        Given: A valid update request with a new unique name
        When: validate_update_request is called
        Then: Returns empty errors list
        """
        mock_repo = Mock()
        mock_repo.get_by_name.return_value = None
        validator = StoreValidator(mock_repo)

        errors = validator.validate_update_request(
            1, make_update_request(name="Enjoei")
        )

        assert errors == []

    def test_update_request_without_fields_should_return_no_errors(self):
        """
        Given: An update request with no fields provided (all None)
        When: validate_update_request is called
        Then: Returns empty errors list (nothing to validate)
        """
        mock_repo = Mock()
        validator = StoreValidator(mock_repo)

        errors = validator.validate_update_request(1, make_update_request())

        assert errors == []

    def test_update_request_with_invalid_type_should_return_error(self):
        """
        Given: An update request with type != 'source_website'
        When: validate_update_request is called
        Then: Returns a 400 INVALID_TYPE error
        """
        mock_repo = Mock()
        request = make_update_request(name="New Name")
        request.data.type = "wrong_type"

        validator = StoreValidator(mock_repo)
        errors = validator.validate_update_request(1, request)

        assert len(errors) == 1
        assert errors[0].code == "INVALID_TYPE"

    def test_update_request_with_empty_name_should_return_error(self):
        """
        Given: An update request with name set to empty string
        When: validate_update_request is called
        Then: Returns a 422 INVALID_VALUE error
        """
        mock_repo = Mock()
        validator = StoreValidator(mock_repo)

        errors = validator.validate_update_request(1, make_update_request(name=""))

        assert len(errors) == 1
        assert errors[0].code == "INVALID_VALUE"
        assert "name" in errors[0].source["pointer"]

    def test_update_request_with_empty_base_url_should_return_error(self):
        """
        Given: An update request with base_url set to empty string
        When: validate_update_request is called
        Then: Returns a 422 INVALID_VALUE error
        """
        mock_repo = Mock()
        validator = StoreValidator(mock_repo)

        errors = validator.validate_update_request(1, make_update_request(base_url=""))

        assert len(errors) == 1
        assert errors[0].code == "INVALID_VALUE"
        assert "base_url" in errors[0].source["pointer"]

    def test_update_request_with_name_from_another_record_should_return_conflict(self):
        """
        Given: The new name belongs to a different source website (id=2)
        When: validate_update_request is called for id=1
        Then: Returns a 409 DUPLICATE_NAME error
        """
        mock_repo = Mock()
        mock_repo.get_by_name.return_value = make_source_website_entity(id=2)
        validator = StoreValidator(mock_repo)

        errors = validator.validate_update_request(
            1, make_update_request(name="Mercado Livre")
        )

        assert len(errors) == 1
        assert errors[0].code == "DUPLICATE_NAME"
        assert errors[0].status == "409"

    def test_update_request_with_own_name_should_return_no_errors(self):
        """
        Given: The new name is the same as the current record (same id)
        When: validate_update_request is called
        Then: Returns empty errors list (not a conflict)
        """
        mock_repo = Mock()
        mock_repo.get_by_name.return_value = make_source_website_entity(id=1)
        validator = StoreValidator(mock_repo)

        errors = validator.validate_update_request(1, make_update_request(name="OLX"))

        assert errors == []
