"""Unit tests for UserValidator"""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from src.app.accounts.entities import User as UserEntity
from src.app.domain.validators.user_validator import UserValidator
from src.app.interfaces.http.schemas.user_schema import (
    UserAttributesForCreation,
    UserAttributesForUpdate,
    UserCreateRequest,
    UserResourceForCreation,
    UserResourceForUpdate,
    UserUpdateRequest,
)


class TestUserValidatorCreate:
    """Tests for validate_create_request method"""

    def test_valid_create_request_should_return_no_errors(self):
        """
        Given: A valid user creation request with unique username and email
        When: validate_create_request is called
        Then: Should return an empty list of errors
        """
        # Arrange
        mock_repository = Mock()
        mock_repository.get_by_username.return_value = None  # Username available
        mock_repository.get_by_email.return_value = None  # Email available

        validator = UserValidator(mock_repository)

        request = UserCreateRequest(
            data=UserResourceForCreation(
                type="users",
                attributes=UserAttributesForCreation(
                    username="newuser",
                    email="newuser@example.com",
                    password="password123",
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                ),
            )
        )

        # Act
        errors = validator.validate_create_request(request)

        # Assert
        assert len(errors) == 0
        mock_repository.get_by_username.assert_called_once_with("newuser")
        mock_repository.get_by_email.assert_called_once_with("newuser@example.com")

    @pytest.mark.parametrize(
        "field_name,field_value,other_fields",
        [
            ("username", "", {"email": "test@example.com", "password": "password123"}),
            ("password", "", {"username": "testuser", "email": "test@example.com"}),
        ],
        ids=["missing_username", "missing_password"],
    )
    def test_create_request_missing_required_field_should_return_error(
        self, field_name, field_value, other_fields
    ):
        """
        Given: A user creation request missing a required field
        When: validate_create_request is called
        Then: Should return an error for the missing field
        """
        # Arrange
        mock_repository = Mock()
        validator = UserValidator(mock_repository)

        # Build attributes dynamically
        attrs_data = {
            field_name: field_value,  # Field being tested (empty)
            **other_fields,  # Other valid fields
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        }

        request = UserCreateRequest(
            data=UserResourceForCreation(
                type="users", attributes=UserAttributesForCreation(**attrs_data)
            )
        )

        # Act
        errors = validator.validate_create_request(request)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "MISSING_FIELD"
        assert errors[0].source["pointer"] == f"/data/attributes/{field_name}"
        assert errors[0].status == "422"
        mock_repository.get_by_username.assert_not_called()
        mock_repository.get_by_email.assert_not_called()

    def test_create_request_invalid_type_should_return_error(self):
        """
        Given: A user creation request with an invalid type
        When: validate_create_request is called
        Then: Should return an error indicating the invalid type
        """
        # Arrange
        mock_repository = Mock()
        validator = UserValidator(mock_repository)

        request = UserCreateRequest(
            data=UserResourceForCreation(
                type="invalid_type",
                attributes=UserAttributesForCreation(
                    username="userwithbadtype",
                    email="userwithbadtype@example.com",
                    password="password123",
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                ),
            )
        )

        # Act
        errors = validator.validate_create_request(request)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "INVALID_TYPE"
        assert errors[0].source["pointer"] == "/data/type"
        assert errors[0].status == "400"
        assert "invalid_type" in errors[0].detail
        mock_repository.get_by_username.assert_not_called()
        mock_repository.get_by_email.assert_not_called()

    def test_create_request_with_empty_email_should_fail_at_pydantic_level(self):
        """
        Given: A user creation request with empty email
        When: UserCreateRequest is instantiated
        Then: Should raise Pydantic ValidationError before reaching our validator
        """
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserCreateRequest(
                data=UserResourceForCreation(
                    type="users",
                    attributes=UserAttributesForCreation(
                        username="testuser",
                        email="",  # Empty email
                        password="password123",
                        is_active=True,
                        is_staff=False,
                        is_superuser=False,
                    ),
                )
            )

        # Verify it's an email validation error
        assert "email" in str(exc_info.value)

    def test_create_request_with_invalid_email_format_should_fail_at_pydantic_level(
        self,
    ):
        """
        Given: A user creation request with invalid email format
        When: UserCreateRequest is instantiated
        Then: Should raise Pydantic ValidationError
        """
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserCreateRequest(
                data=UserResourceForCreation(
                    type="users",
                    attributes=UserAttributesForCreation(
                        username="testuser",
                        email="not-an-email",  # Invalid format
                        password="password123",
                        is_active=True,
                        is_staff=False,
                        is_superuser=False,
                    ),
                )
            )

        # Verify it's an email validation error
        assert "email" in str(exc_info.value)

    @pytest.mark.parametrize(
        "field_name,duplicate_value",
        [
            ("username", "existinguser"),
            ("email", "existing@example.com"),
        ],
        ids=["duplicate_username", "duplicate_email"],
    )
    def test_create_request_with_duplicate_field_should_return_error(
        self, field_name, duplicate_value
    ):
        """
        Given: A user creation request with duplicate username or email
        When: validate_create_request is called
        Then: Should return a conflict error for the duplicate field
        """
        # Arrange
        mock_repository = Mock()
        existing_user = UserEntity(
            id=1,
            username="existinguser",
            email="existing@example.com",
            hashed_password="hashed",
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )

        # Mock repository returns existing user for the duplicate field
        if field_name == "username":
            mock_repository.get_by_username.return_value = existing_user
            mock_repository.get_by_email.return_value = None
        else:
            mock_repository.get_by_username.return_value = None
            mock_repository.get_by_email.return_value = existing_user

        validator = UserValidator(mock_repository)

        attrs_data = {
            "username": duplicate_value if field_name == "username" else "newuser",
            "email": duplicate_value if field_name == "email" else "new@example.com",
            "password": "password123",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        }

        request = UserCreateRequest(
            data=UserResourceForCreation(
                type="users", attributes=UserAttributesForCreation(**attrs_data)
            )
        )

        # Act
        errors = validator.validate_create_request(request)

        # Assert
        assert len(errors) == 1
        if field_name == "username":
            assert errors[0].code == "DUPLICATE_USERNAME"
        else:
            assert errors[0].code == "DUPLICATE_EMAIL"
        assert errors[0].source["pointer"] == f"/data/attributes/{field_name}"
        assert errors[0].status == "409"
        assert duplicate_value in errors[0].detail


class TestUserValidatorUpdate:
    """Tests for validate_update_request method"""

    def test_valid_update_request_should_return_no_errors(self):
        """
        Given: A valid user update request with unique username
        When: validate_update_request is called
        Then: Should return an empty list of errors
        """
        # Arrange
        mock_repository = Mock()
        mock_repository.get_by_username.return_value = None
        mock_repository.get_by_email.return_value = None

        validator = UserValidator(mock_repository)

        request = UserUpdateRequest(
            data=UserResourceForUpdate(
                type="users",
                attributes=UserAttributesForUpdate(
                    username="updateduser",
                    email="updated@example.com",
                ),
            )
        )

        # Act
        errors = validator.validate_update_request(request, user_id=1)

        # Assert
        assert len(errors) == 0

    def test_update_request_invalid_type_should_return_error(self):
        """
        Given: An update request with invalid type
        When: validate_update_request is called
        Then: Should return an error for invalid type
        """
        # Arrange
        mock_repository = Mock()
        mock_repository.get_by_username.return_value = None  # No duplicate
        mock_repository.get_by_email.return_value = None  # No duplicate
        validator = UserValidator(mock_repository)

        request = UserUpdateRequest(
            data=UserResourceForUpdate(
                type="invalid_type",
                attributes=UserAttributesForUpdate(username="newname"),
            )
        )

        # Act
        errors = validator.validate_update_request(request, user_id=1)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "INVALID_TYPE"
        assert errors[0].status == "400"

    def test_update_request_with_no_fields_should_return_error(self):
        """
        Given: An update request with no fields provided
        When: validate_update_request is called
        Then: Should return an EMPTY_UPDATE error
        """
        # Arrange
        mock_repository = Mock()
        validator = UserValidator(mock_repository)

        request = UserUpdateRequest(
            data=UserResourceForUpdate(
                type="users",
                attributes=UserAttributesForUpdate(),  # No fields
            )
        )

        # Act
        errors = validator.validate_update_request(request, user_id=1)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "EMPTY_UPDATE"
        assert errors[0].status == "422"
        assert errors[0].source["pointer"] == "/data/attributes"

    @pytest.mark.parametrize(
        "field_name,duplicate_value",
        [
            ("username", "otheruser"),
            ("email", "other@example.com"),
        ],
        ids=["duplicate_username", "duplicate_email"],
    )
    def test_update_request_with_duplicate_field_from_another_user_should_return_error(
        self, field_name, duplicate_value
    ):
        """
        Given: An update request with username/email already used by another user
        When: validate_update_request is called
        Then: Should return a conflict error
        """
        # Arrange
        mock_repository = Mock()
        other_user = UserEntity(
            id=2,  # Different user ID
            username="otheruser",
            email="other@example.com",
            hashed_password="hashed",
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )

        if field_name == "username":
            mock_repository.get_by_username.return_value = other_user
            mock_repository.get_by_email.return_value = None
        else:
            mock_repository.get_by_username.return_value = None
            mock_repository.get_by_email.return_value = other_user

        validator = UserValidator(mock_repository)

        attrs_data = {}
        if field_name == "username":
            attrs_data["username"] = duplicate_value
        else:
            attrs_data["email"] = duplicate_value

        request = UserUpdateRequest(
            data=UserResourceForUpdate(
                type="users", attributes=UserAttributesForUpdate(**attrs_data)
            )
        )

        # Act
        errors = validator.validate_update_request(request, user_id=1)

        # Assert
        assert len(errors) == 1
        if field_name == "username":
            assert errors[0].code == "DUPLICATE_USERNAME"
        else:
            assert errors[0].code == "DUPLICATE_EMAIL"
        assert errors[0].status == "409"

    def test_update_request_with_own_username_should_return_no_errors(self):
        """
        Given: An update request using the same username (user updating their own)
        When: validate_update_request is called
        Then: Should return no errors (allowed to keep same username)
        """
        # Arrange
        mock_repository = Mock()
        current_user = UserEntity(
            id=1,
            username="sameuser",
            email="same@example.com",
            hashed_password="hashed",
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        mock_repository.get_by_username.return_value = current_user
        mock_repository.get_by_email.return_value = None

        validator = UserValidator(mock_repository)

        request = UserUpdateRequest(
            data=UserResourceForUpdate(
                type="users", attributes=UserAttributesForUpdate(username="sameuser")
            )
        )

        # Act
        errors = validator.validate_update_request(request, user_id=1)

        # Assert
        assert len(errors) == 0


class TestUserValidatorDelete:
    """Tests for validate_delete_request method"""

    def test_valid_delete_request_should_return_no_errors(self):
        """
        Given: A delete request for an existing user
        When: validate_delete_request is called
        Then: Should return no errors
        """
        # Arrange
        mock_repository = Mock()
        existing_user = UserEntity(
            id=1,
            username="usertoDelete",
            email="delete@example.com",
            hashed_password="hashed",
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        mock_repository.get_by_id.return_value = existing_user

        validator = UserValidator(mock_repository)

        # Act
        errors = validator.validate_delete_request(user_id=1)

        # Assert
        assert len(errors) == 0
        mock_repository.get_by_id.assert_called_once_with(1)

    def test_delete_request_for_nonexistent_user_should_return_error(self):
        """
        Given: A delete request for a non-existent user
        When: validate_delete_request is called
        Then: Should return a NOT_FOUND error
        """
        # Arrange
        mock_repository = Mock()
        mock_repository.get_by_id.return_value = None

        validator = UserValidator(mock_repository)

        # Act
        errors = validator.validate_delete_request(user_id=999)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "NOT_FOUND"
        assert errors[0].status == "404"
        assert "999" in errors[0].detail
        assert errors[0].source["pointer"] == "/data/id"


class TestUserValidatorGetByUsername:
    """Tests for validate_get_by_username_request method"""

    def test_valid_get_by_username_request_should_return_no_errors(self):
        """
        Given: A valid username is provided
        When: validate_get_by_username_request is called
        Then: Should return no errors
        """
        # Arrange
        mock_repository = Mock()
        validator = UserValidator(mock_repository)

        # Act
        errors = validator.validate_get_by_username_request(username="validuser")

        # Assert
        assert len(errors) == 0

    @pytest.mark.parametrize(
        "username", ["", "   "], ids=["empty_string", "whitespace_only"]
    )
    def test_get_by_username_with_empty_username_should_return_error(self, username):
        """
        Given: An empty or whitespace-only username
        When: validate_get_by_username_request is called
        Then: Should return a MISSING_FIELD error
        """
        # Arrange
        mock_repository = Mock()
        validator = UserValidator(mock_repository)

        # Act
        errors = validator.validate_get_by_username_request(username=username)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "MISSING_FIELD"
        assert errors[0].status == "400"
        assert errors[0].source["pointer"] == "/username"


class TestUserValidatorGetByEmail:
    """Tests for validate_get_by_email_request method"""

    def test_valid_get_by_email_request_should_return_no_errors(self):
        """
        Given: A valid email is provided
        When: validate_get_by_email_request is called
        Then: Should return no errors
        """
        # Arrange
        mock_repository = Mock()
        validator = UserValidator(mock_repository)

        # Act
        errors = validator.validate_get_by_email_request(email="valid@example.com")

        # Assert
        assert len(errors) == 0

    @pytest.mark.parametrize(
        "email", ["", "   "], ids=["empty_string", "whitespace_only"]
    )
    def test_get_by_email_with_empty_email_should_return_error(self, email):
        """
        Given: An empty or whitespace-only email
        When: validate_get_by_email_request is called
        Then: Should return a MISSING_FIELD error
        """
        # Arrange
        mock_repository = Mock()
        validator = UserValidator(mock_repository)

        # Act
        errors = validator.validate_get_by_email_request(email=email)

        # Assert
        assert len(errors) == 1
        assert errors[0].code == "MISSING_FIELD"
        assert errors[0].status == "400"
        assert errors[0].source["pointer"] == "/email"
