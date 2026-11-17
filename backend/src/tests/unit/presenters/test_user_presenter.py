"""
Unit tests for User Presenter.

Tests presentation layer (JSON:API formatting) with fixtures.
Following Given/When/Then pattern for clarity.
"""

from datetime import datetime

import pytest
from fastapi.responses import JSONResponse

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.user_presenter import UserPresenter
from src.common.jsonapi import JsonApiError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_user_entity():
    """Sample user entity for testing."""
    return UserEntity(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$hashed_password",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_validation_errors():
    """Sample validation errors for testing."""
    return [
        JsonApiError(
            status="422",
            code="MISSING_FIELD",
            title="Validation error",
            detail="Field 'username' is required",
            source={"pointer": "/data/attributes/username"},
        ),
        JsonApiError(
            status="422",
            code="DUPLICATE_FIELD",
            title="Validation error",
            detail="Field 'email' already exists",
            source={"pointer": "/data/attributes/email"},
        ),
    ]


# ============================================================================
# UserPresenter.handle_success Tests
# ============================================================================


class TestUserPresenterHandleSuccess:
    """Tests for UserPresenter.handle_success()."""

    def test_handle_success_should_return_jsonapi_response(self, sample_user_entity):
        """
        Given: A valid user entity
        When: UserPresenter.handle_success() is called
        Then: Should return UserReadResponse with correct JSON:API structure
        """
        # When
        response = UserPresenter.handle_success(sample_user_entity)

        # Then
        assert response.data.type == "users"
        assert response.data.id == "1"
        assert response.data.attributes.username == "testuser"
        assert response.data.attributes.email == "test@example.com"
        assert response.data.attributes.is_active is True
        assert response.data.attributes.is_staff is False
        assert response.data.attributes.is_superuser is False

    def test_handle_success_should_not_expose_hashed_password(self, sample_user_entity):
        """
        Given: A user entity with hashed_password
        When: UserPresenter.handle_success() is called
        Then: Should NOT include hashed_password in attributes
        """
        # When
        response = UserPresenter.handle_success(sample_user_entity)

        # Then
        attributes_dict = response.data.attributes.model_dump()
        assert "hashed_password" not in attributes_dict

    def test_handle_success_should_include_timestamps(self, sample_user_entity):
        """
        Given: A user entity with created_at and updated_at
        When: UserPresenter.handle_success() is called
        Then: Should include timestamps in attributes
        """
        # When
        response = UserPresenter.handle_success(sample_user_entity)

        # Then
        assert response.data.attributes.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert response.data.attributes.updated_at == datetime(2025, 1, 1, 12, 0, 0)


# ============================================================================
# UserPresenter.handle_validation_errors Tests
# ============================================================================


class TestUserPresenterHandleValidationErrors:
    """Tests for UserPresenter.handle_validation_errors()."""

    def test_handle_validation_errors_should_return_jsonapi_error_response(
        self, sample_validation_errors
    ):
        """
        Given: A list of validation errors
        When: UserPresenter.handle_validation_errors() is called
        Then: Should return JSONResponse with correct JSON:API error structure
        """
        # When
        response = UserPresenter.handle_validation_errors(sample_validation_errors)

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        assert response.media_type == "application/vnd.api+json"

    def test_handle_validation_errors_should_include_all_errors(
        self, sample_validation_errors
    ):
        """
        Given: Multiple validation errors
        When: UserPresenter.handle_validation_errors() is called
        Then: Should include all errors in the response
        """
        # When
        response = UserPresenter.handle_validation_errors(sample_validation_errors)
        content = response.body.decode("utf-8")

        # Then
        assert "MISSING_FIELD" in content
        assert "DUPLICATE_FIELD" in content
        assert "username" in content
        assert "email" in content

    def test_handle_validation_errors_should_use_first_error_status_code(self):
        """
        Given: Validation errors with status 400
        When: UserPresenter.handle_validation_errors() is called
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
        response = UserPresenter.handle_validation_errors(errors)

        # Then
        assert response.status_code == 400


# ============================================================================
# UserPresenter.handle_not_found Tests
# ============================================================================


class TestUserPresenterHandleNotFound:
    """Tests for UserPresenter.handle_not_found()."""

    def test_handle_not_found_should_return_404_jsonapi_error(self):
        """
        Given: User identifier and pointer
        When: UserPresenter.handle_not_found() is called
        Then: Should return 404 JSONResponse with JSON:API error structure
        """
        # When
        response = UserPresenter.handle_not_found(
            identifier="id=999", pointer="/data/attributes/id"
        )

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        assert response.media_type == "application/vnd.api+json"

    def test_handle_not_found_should_include_identifier_in_detail(self):
        """
        Given: Specific user identifier
        When: UserPresenter.handle_not_found() is called
        Then: Should include identifier in error detail
        """
        # When
        response = UserPresenter.handle_not_found(
            identifier="username='nonexistent'", pointer="/data/attributes/username"
        )
        content = response.body.decode("utf-8")

        # Then
        assert "nonexistent" in content
        assert "NOT_FOUND" in content
        assert "404" in content

    def test_handle_not_found_should_include_correct_error_structure(self):
        """
        Given: User identifier
        When: UserPresenter.handle_not_found() is called
        Then: Should have correct JSON:API error fields
        """
        # When
        response = UserPresenter.handle_not_found(
            identifier="id=123", pointer="/data/id"
        )
        content = response.body.decode("utf-8")

        # Then
        assert '"status":"404"' in content or '"status": "404"' in content
        assert '"code":"NOT_FOUND"' in content or '"code": "NOT_FOUND"' in content
        assert (
            '"title":"User not found"' in content
            or '"title": "User not found"' in content
        )
