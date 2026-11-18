"""Unit tests for SearchConfigValidator."""

from datetime import time
from unittest.mock import Mock

import pytest

from src.app.domain.validators.search_config_validator import SearchConfigValidator
from src.app.interfaces.http.schemas.search_config_schema import (
    SearchConfigAttributesForCreation,
    SearchConfigAttributesForUpdate,
    SearchConfigCreateRequest,
    SearchConfigResourceForCreation,
    SearchConfigResourceForUpdate,
    SearchConfigUpdateRequest,
)
from src.app.searches.entities import SavedSearch

# ============================================================================
# Helpers
# ============================================================================


def make_create_request(**overrides) -> SearchConfigCreateRequest:
    attrs_data = {
        "search_term": overrides.pop("search_term", "iPhone 13"),
        "user_id": overrides.pop("user_id", 1),
        "is_active": overrides.pop("is_active", True),
        "frequency_days": overrides.pop("frequency_days", 1),
        "preferred_time": overrides.pop("preferred_time", time(0, 0)),
        "source_website_ids": overrides.pop("source_website_ids", []),
        **overrides,
    }
    attrs = SearchConfigAttributesForCreation(**attrs_data)
    return SearchConfigCreateRequest(
        data=SearchConfigResourceForCreation(type="search_config", attributes=attrs)
    )


def make_update_request(**overrides) -> SearchConfigUpdateRequest:
    attrs = SearchConfigAttributesForUpdate(**overrides)
    return SearchConfigUpdateRequest(
        data=SearchConfigResourceForUpdate(type="search_config", attributes=attrs)
    )


def make_search_config_entity(**overrides) -> SavedSearch:
    defaults = {
        "id": 1,
        "search_term": "iPhone 13",
        "is_active": True,
        "frequency_days": 1,
        "preferred_time": time(0, 0),
        "user_id": 1,
        "source_website_ids": [],
    }
    defaults.update(overrides)
    return SavedSearch(**defaults)


# ============================================================================
# Tests: validate_create_request
# ============================================================================


class TestSearchConfigValidatorCreate:
    """Tests for SearchConfigValidator.validate_create_request"""

    def test_valid_create_request_returns_no_errors(self):
        """
        Given: A valid create request with required fields and no conflicts
        When: validate_create_request is called
        Then: Returns empty errors list
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        mock_sc_repo.get_by_search_term_and_user_id.return_value = None
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_create_request(make_create_request())

        assert errors == []

    def test_create_with_invalid_type_returns_400(self):
        """
        Given: type != 'search_config'
        When: validate_create_request is called
        Then: Returns 400 INVALID_TYPE error
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        request = make_create_request()
        request.data.type = "search_configs"

        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)
        errors = validator.validate_create_request(request)

        assert len(errors) == 1
        assert errors[0].code == "INVALID_TYPE"
        assert errors[0].status == "400"

    @pytest.mark.parametrize("bad_term", ["", "   "])
    def test_create_with_empty_search_term_returns_422(self, bad_term):
        """
        Given: search_term is empty or whitespace-only
        When: validate_create_request is called
        Then: Returns 422 MISSING_FIELD error
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        request = make_create_request(search_term=bad_term)
        errors = validator.validate_create_request(request)

        assert any(e.code == "MISSING_FIELD" for e in errors)

    def test_create_without_user_id_returns_422(self):
        """
        Given: user_id is None
        When: validate_create_request is called
        Then: Returns 422 MISSING_FIELD error
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        request = make_create_request()
        request.data.attributes.user_id = None
        errors = validator.validate_create_request(request)

        assert any(e.code == "MISSING_FIELD" for e in errors)
        assert any("user_id" in e.source["pointer"] for e in errors)

    @pytest.mark.parametrize("bad_days", [0, -1, -10])
    def test_create_with_invalid_frequency_days_returns_422(self, bad_days):
        """
        Given: frequency_days <= 0
        When: validate_create_request is called
        Then: Returns 422 INVALID_FIELD error
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        request = make_create_request(frequency_days=bad_days)
        errors = validator.validate_create_request(request)

        assert any(e.code == "INVALID_FIELD" for e in errors)
        assert any("frequency_days" in e.source["pointer"] for e in errors)

    def test_create_with_nonexistent_source_website_returns_404(self):
        """
        Given: A source_website_id that does not exist
        When: validate_create_request is called
        Then: Returns 404 SOURCE_WEBSITE_NOT_FOUND error
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        mock_sw_repo.get_by_id.return_value = None
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        request = make_create_request(source_website_ids=[999])
        errors = validator.validate_create_request(request)

        assert len(errors) == 1
        assert errors[0].code == "SOURCE_WEBSITE_NOT_FOUND"
        assert errors[0].status == "404"

    def test_create_with_duplicate_search_term_for_same_user_returns_409(self):
        """
        Given: search_term already exists for this user_id
        When: validate_create_request is called
        Then: Returns 409 DUPLICATE_SEARCH_TERM error
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        mock_sc_repo.get_by_search_term_and_user_id.return_value = (
            make_search_config_entity()
        )
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_create_request(make_create_request())

        assert len(errors) == 1
        assert errors[0].code == "DUPLICATE_SEARCH_TERM"
        assert errors[0].status == "409"

    def test_create_with_same_term_different_user_returns_no_errors(self):
        """
        Given: Same search_term but for a different user_id (no conflict)
        When: validate_create_request is called
        Then: Returns empty errors (uniqueness is per user)
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        mock_sc_repo.get_by_search_term_and_user_id.return_value = None
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_create_request(make_create_request(user_id=2))

        assert errors == []


# ============================================================================
# Tests: validate_update_request
# ============================================================================


class TestSearchConfigValidatorUpdate:
    """Tests for SearchConfigValidator.validate_update_request"""

    def test_valid_update_request_returns_no_errors(self):
        """
        Given: A valid update request with no conflicts
        When: validate_update_request is called
        Then: Returns empty errors list
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        existing = make_search_config_entity(id=1)
        mock_sc_repo.get_by_id.return_value = existing
        mock_sc_repo.get_by_search_term_and_user_id.return_value = None
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_update_request(
            1, make_update_request(search_term="Samsung S23")
        )

        assert errors == []

    def test_update_with_invalid_type_returns_400(self):
        """
        Given: type != 'search_config'
        When: validate_update_request is called
        Then: Returns 400 INVALID_TYPE error
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        request = make_update_request()
        request.data.type = "wrong"
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_update_request(1, request)

        assert any(e.code == "INVALID_TYPE" for e in errors)

    def test_update_with_empty_search_term_returns_422(self):
        """
        Given: search_term is explicitly set to empty string
        When: validate_update_request is called
        Then: Returns 422 INVALID_VALUE error
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_update_request(
            1, make_update_request(search_term="")
        )

        assert any(e.code == "INVALID_VALUE" for e in errors)

    @pytest.mark.parametrize("bad_days", [0, -5])
    def test_update_with_invalid_frequency_days_returns_422(self, bad_days):
        """
        Given: frequency_days <= 0
        When: validate_update_request is called
        Then: Returns 422 INVALID_FIELD error
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_update_request(
            1, make_update_request(frequency_days=bad_days)
        )

        assert any(e.code == "INVALID_FIELD" for e in errors)

    def test_update_with_nonexistent_source_website_returns_404(self):
        """
        Given: A source_website_id that does not exist
        When: validate_update_request is called
        Then: Returns 404 SOURCE_WEBSITE_NOT_FOUND
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        mock_sw_repo.get_by_id.return_value = None
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_update_request(
            1, make_update_request(source_website_ids=[999])
        )

        assert any(e.code == "SOURCE_WEBSITE_NOT_FOUND" for e in errors)

    def test_update_with_duplicate_search_term_for_same_user_returns_409(self):
        """
        Given: search_term already exists for this user under a different id
        When: validate_update_request is called
        Then: Returns 409 DUPLICATE_SEARCH_TERM
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        existing_self = make_search_config_entity(id=1, user_id=1)
        duplicate = make_search_config_entity(
            id=2, search_term="Samsung S23", user_id=1
        )
        mock_sc_repo.get_by_id.return_value = existing_self
        mock_sc_repo.get_by_search_term_and_user_id.return_value = duplicate
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_update_request(
            1, make_update_request(search_term="Samsung S23")
        )

        assert any(e.code == "DUPLICATE_SEARCH_TERM" for e in errors)

    def test_update_with_same_search_term_same_record_returns_no_error(self):
        """
        Given: search_term already exists but belongs to the same record (no real conflict)
        When: validate_update_request is called
        Then: Returns empty errors
        """
        mock_sc_repo = Mock()
        mock_sw_repo = Mock()
        existing = make_search_config_entity(id=1, search_term="iPhone 13", user_id=1)
        mock_sc_repo.get_by_id.return_value = existing
        # Same record returned — duplicate.id == search_config_id
        mock_sc_repo.get_by_search_term_and_user_id.return_value = existing
        validator = SearchConfigValidator(mock_sc_repo, mock_sw_repo)

        errors = validator.validate_update_request(
            1, make_update_request(search_term="iPhone 13")
        )

        assert errors == []
