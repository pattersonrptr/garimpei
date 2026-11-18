"""Unit tests for SearchExecutionLogValidator."""

from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from src.app.domain.validators.search_execution_log_validator import (
    SearchExecutionLogValidator,
)
from src.app.searches.entities import SavedSearch

# ============================================================================
# Minimal stubs to feed into the validator (mimics internal system usage)
# ============================================================================


class _Attrs(BaseModel):
    search_config_id: int
    status: str | None = "pending"
    results_count: int | None = None
    error_message: str | None = None


class _Data(BaseModel):
    type: str = "search_execution_log"
    attributes: _Attrs


class _Request(BaseModel):
    data: _Data


def make_request(**overrides) -> _Request:
    attrs = {"search_config_id": 1, **overrides}
    return _Request(data=_Data(attributes=_Attrs(**attrs)))


def make_request_with_type(type_: str, **attr_overrides) -> _Request:
    attrs = {"search_config_id": 1, **attr_overrides}
    return _Request(data=_Data(type=type_, attributes=_Attrs(**attrs)))


def make_search_config_entity(id: int = 1) -> SavedSearch:
    return SavedSearch(id=id, search_term="laptop", user_id=1)


# ============================================================================
# Tests
# ============================================================================


class TestSearchExecutionLogValidatorCreate:
    """Tests for SearchExecutionLogValidator.validate_create_request"""

    def test_valid_request_should_return_no_errors(self):
        """
        Given: A valid request with search_config_id=1
        When: validate_create_request is called
        Then: Returns empty list (no errors)
        """
        search_execution_log_repo = Mock()
        search_config_repo = Mock()
        search_config_repo.get_by_id.return_value = make_search_config_entity()

        validator = SearchExecutionLogValidator(
            search_execution_log_repo, search_config_repo
        )
        errors = validator.validate_create_request(make_request())

        assert errors == []

    def test_invalid_type_should_return_400_invalid_type(self):
        """
        Given: type='search_execution_logs' (plural — wrong)
        When: validate_create_request is called
        Then: Returns one error with status '400' and code 'INVALID_TYPE'
        """
        validator = SearchExecutionLogValidator(Mock(), Mock())
        errors = validator.validate_create_request(
            make_request_with_type("search_execution_logs")
        )

        assert len(errors) == 1
        assert errors[0].status == "400"
        assert errors[0].code == "INVALID_TYPE"

    @pytest.mark.parametrize("search_config_id", [0, -1])
    def test_invalid_search_config_id_should_return_missing_field(
        self, search_config_id
    ):
        """
        Given: search_config_id <= 0
        When: validate_create_request is called
        Then: Returns error with code 'MISSING_FIELD'
        """
        validator = SearchExecutionLogValidator(Mock(), Mock())
        errors = validator.validate_create_request(
            make_request(search_config_id=search_config_id)
        )

        assert any(e.code == "MISSING_FIELD" for e in errors)

    @pytest.mark.parametrize("status", ["unknown", "PENDING", "done", "cancelled"])
    def test_invalid_status_should_return_invalid_field(self, status):
        """
        Given: An invalid status value
        When: validate_create_request is called
        Then: Returns error with code 'INVALID_FIELD'
        """
        validator = SearchExecutionLogValidator(Mock(), Mock())
        errors = validator.validate_create_request(make_request(status=status))

        assert any(e.code == "INVALID_FIELD" for e in errors)

    @pytest.mark.parametrize("status", ["pending", "running", "success", "failed"])
    def test_valid_status_should_pass(self, status):
        """
        Given: A valid status value
        When: validate_create_request is called
        Then: No errors
        """
        search_config_repo = Mock()
        search_config_repo.get_by_id.return_value = make_search_config_entity()

        validator = SearchExecutionLogValidator(Mock(), search_config_repo)
        errors = validator.validate_create_request(make_request(status=status))

        assert errors == []

    @pytest.mark.parametrize("results_count", [-1, -100])
    def test_negative_results_count_should_return_invalid_field(self, results_count):
        """
        Given: results_count < 0
        When: validate_create_request is called
        Then: Returns error with code 'INVALID_FIELD'
        """
        validator = SearchExecutionLogValidator(Mock(), Mock())
        errors = validator.validate_create_request(
            make_request(results_count=results_count)
        )

        assert any(e.code == "INVALID_FIELD" for e in errors)

    def test_results_count_zero_should_pass(self):
        """
        Given: results_count=0 (no results found — valid)
        When: validate_create_request is called
        Then: No errors
        """
        search_config_repo = Mock()
        search_config_repo.get_by_id.return_value = make_search_config_entity()

        validator = SearchExecutionLogValidator(Mock(), search_config_repo)
        errors = validator.validate_create_request(make_request(results_count=0))

        assert errors == []

    def test_nonexistent_search_config_should_return_404_not_found(self):
        """
        Given: search_config_id references a non-existent config
        When: validate_create_request is called
        Then: Returns error with code 'SEARCH_CONFIG_NOT_FOUND' and status '404'
        """
        search_config_repo = Mock()
        search_config_repo.get_by_id.return_value = None

        validator = SearchExecutionLogValidator(Mock(), search_config_repo)
        errors = validator.validate_create_request(make_request())

        assert len(errors) == 1
        assert errors[0].status == "404"
        assert errors[0].code == "SEARCH_CONFIG_NOT_FOUND"
