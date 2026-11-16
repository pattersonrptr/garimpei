"""
Unit tests for User Use Cases.

Tests business logic layer with mocked repositories.
Following Given/When/Then pattern for clarity.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.app.accounts.entities import User as UserEntity
from src.app.interfaces.http.schemas.user_schema import (
    UserAttributesForCreation,
    UserAttributesForUpdate,
    UserCreateRequest,
    UserResourceForCreation,
    UserResourceForUpdate,
    UserUpdateRequest,
)
from src.app.use_cases.user_use_cases import (
    CreateUserUseCase,
    DeleteUserUseCase,
    GetAllUsersUseCase,
    GetUserByEmailUseCase,
    GetUserByIdUseCase,
    GetUserByUsernameUseCase,
    UpdateUserUseCase,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_user_repo():
    """Mock repository for testing use cases in isolation."""
    return Mock()


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
def sample_create_request():
    """Sample user creation request."""
    return UserCreateRequest(
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


@pytest.fixture
def sample_update_request():
    """Sample user update request."""
    return UserUpdateRequest(
        data=UserResourceForUpdate(
            type="users",
            attributes=UserAttributesForUpdate(
                username="updateduser",
                email="updated@example.com",
            ),
        )
    )


# ============================================================================
# CreateUserUseCase Tests
# ============================================================================


class TestCreateUserUseCase:
    """Tests for CreateUserUseCase."""

    def test_execute_should_create_user_successfully(
        self, mock_user_repo, sample_create_request, sample_user_entity
    ):
        """
        Given: A valid user creation request and hashed password
        When: CreateUserUseCase.execute() is called
        Then: Should call repository.create() and return created user
        """
        # Given
        mock_user_repo.create.return_value = sample_user_entity
        use_case = CreateUserUseCase(mock_user_repo)
        hashed_password = "$2b$12$hashed_password"

        # When
        result = use_case.execute(sample_create_request, hashed_password)

        # Then
        assert result == sample_user_entity
        mock_user_repo.create.assert_called_once()

        # Verify the entity passed to repository has correct attributes
        call_args = mock_user_repo.create.call_args[0][0]
        assert call_args.username == "newuser"
        assert call_args.email == "newuser@example.com"
        assert call_args.hashed_password == hashed_password
        assert call_args.is_active is True
        assert call_args.is_staff is False
        assert call_args.is_superuser is False

    def test_execute_should_use_default_values_when_not_provided(self, mock_user_repo):
        """
        Given: A user creation request without optional fields
        When: CreateUserUseCase.execute() is called
        Then: Should use default values (is_active=True, is_staff=False, is_superuser=False)
        """
        # Given
        create_request = UserCreateRequest(
            data=UserResourceForCreation(
                type="users",
                attributes=UserAttributesForCreation(
                    username="newuser",
                    email="newuser@example.com",
                    password="password123",
                ),
            )
        )
        mock_user_repo.create.return_value = UserEntity(
            id=1,
            username="newuser",
            email="newuser@example.com",
            hashed_password="$2b$12$hashed",
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        use_case = CreateUserUseCase(mock_user_repo)

        # When
        use_case.execute(create_request, "$2b$12$hashed")

        # Then
        call_args = mock_user_repo.create.call_args[0][0]
        assert call_args.is_active is True
        assert call_args.is_staff is False
        assert call_args.is_superuser is False


# ============================================================================
# GetUserByIdUseCase Tests
# ============================================================================


class TestGetUserByIdUseCase:
    """Tests for GetUserByIdUseCase."""

    def test_execute_should_return_user_when_exists(
        self, mock_user_repo, sample_user_entity
    ):
        """
        Given: A user ID that exists in the repository
        When: GetUserByIdUseCase.execute() is called
        Then: Should return the user entity
        """
        # Given
        mock_user_repo.get_by_id.return_value = sample_user_entity
        use_case = GetUserByIdUseCase(mock_user_repo)

        # When
        result = use_case.execute(1)

        # Then
        assert result == sample_user_entity
        mock_user_repo.get_by_id.assert_called_once_with(1)

    def test_execute_should_return_none_when_user_not_found(self, mock_user_repo):
        """
        Given: A user ID that does not exist
        When: GetUserByIdUseCase.execute() is called
        Then: Should return None
        """
        # Given
        mock_user_repo.get_by_id.return_value = None
        use_case = GetUserByIdUseCase(mock_user_repo)

        # When
        result = use_case.execute(999)

        # Then
        assert result is None
        mock_user_repo.get_by_id.assert_called_once_with(999)


# ============================================================================
# GetUserByUsernameUseCase Tests
# ============================================================================


class TestGetUserByUsernameUseCase:
    """Tests for GetUserByUsernameUseCase."""

    def test_execute_should_return_user_when_exists(
        self, mock_user_repo, sample_user_entity
    ):
        """
        Given: A username that exists in the repository
        When: GetUserByUsernameUseCase.execute() is called
        Then: Should return the user entity
        """
        # Given
        mock_user_repo.get_by_username.return_value = sample_user_entity
        use_case = GetUserByUsernameUseCase(mock_user_repo)

        # When
        result = use_case.execute("testuser")

        # Then
        assert result == sample_user_entity
        mock_user_repo.get_by_username.assert_called_once_with("testuser")

    def test_execute_should_return_none_when_user_not_found(self, mock_user_repo):
        """
        Given: A username that does not exist
        When: GetUserByUsernameUseCase.execute() is called
        Then: Should return None
        """
        # Given
        mock_user_repo.get_by_username.return_value = None
        use_case = GetUserByUsernameUseCase(mock_user_repo)

        # When
        result = use_case.execute("nonexistent")

        # Then
        assert result is None
        mock_user_repo.get_by_username.assert_called_once_with("nonexistent")


# ============================================================================
# GetUserByEmailUseCase Tests
# ============================================================================


class TestGetUserByEmailUseCase:
    """Tests for GetUserByEmailUseCase."""

    def test_execute_should_return_user_when_exists(
        self, mock_user_repo, sample_user_entity
    ):
        """
        Given: An email that exists in the repository
        When: GetUserByEmailUseCase.execute() is called
        Then: Should return the user entity
        """
        # Given
        mock_user_repo.get_by_email.return_value = sample_user_entity
        use_case = GetUserByEmailUseCase(mock_user_repo)

        # When
        result = use_case.execute("test@example.com")

        # Then
        assert result == sample_user_entity
        mock_user_repo.get_by_email.assert_called_once_with("test@example.com")

    def test_execute_should_return_none_when_user_not_found(self, mock_user_repo):
        """
        Given: An email that does not exist
        When: GetUserByEmailUseCase.execute() is called
        Then: Should return None
        """
        # Given
        mock_user_repo.get_by_email.return_value = None
        use_case = GetUserByEmailUseCase(mock_user_repo)

        # When
        result = use_case.execute("nonexistent@example.com")

        # Then
        assert result is None
        mock_user_repo.get_by_email.assert_called_once_with("nonexistent@example.com")


# ============================================================================
# GetAllUsersUseCase Tests
# ============================================================================


class TestGetAllUsersUseCase:
    """Tests for GetAllUsersUseCase."""

    def test_execute_should_return_all_users(self, mock_user_repo):
        """
        Given: Multiple users in the repository
        When: GetAllUsersUseCase.execute() is called
        Then: Should return list of all users
        """
        # Given
        users = [
            UserEntity(
                id=1,
                username="user1",
                email="user1@example.com",
                hashed_password="hash1",
            ),
            UserEntity(
                id=2,
                username="user2",
                email="user2@example.com",
                hashed_password="hash2",
            ),
            UserEntity(
                id=3,
                username="user3",
                email="user3@example.com",
                hashed_password="hash3",
            ),
        ]
        mock_user_repo.get_all.return_value = users
        use_case = GetAllUsersUseCase(mock_user_repo)

        # When
        result = use_case.execute()

        # Then
        assert result == users
        assert len(result) == 3
        mock_user_repo.get_all.assert_called_once()

    def test_execute_should_return_empty_list_when_no_users(self, mock_user_repo):
        """
        Given: No users in the repository
        When: GetAllUsersUseCase.execute() is called
        Then: Should return empty list
        """
        # Given
        mock_user_repo.get_all.return_value = []
        use_case = GetAllUsersUseCase(mock_user_repo)

        # When
        result = use_case.execute()

        # Then
        assert result == []
        mock_user_repo.get_all.assert_called_once()


# ============================================================================
# UpdateUserUseCase Tests
# ============================================================================


class TestUpdateUserUseCase:
    """Tests for UpdateUserUseCase."""

    def test_execute_should_update_user_successfully(
        self, mock_user_repo, sample_user_entity, sample_update_request
    ):
        """
        Given: An existing user and valid update data
        When: UpdateUserUseCase.execute() is called
        Then: Should update user attributes and call repository.update()
        """
        # Given
        mock_user_repo.get_by_id.return_value = sample_user_entity
        updated_user = UserEntity(
            id=1,
            username="updateduser",
            email="updated@example.com",
            hashed_password="$2b$12$hashed_password",
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        mock_user_repo.update.return_value = updated_user
        use_case = UpdateUserUseCase(mock_user_repo)

        # When
        result = use_case.execute(1, sample_update_request)

        # Then
        assert result == updated_user
        mock_user_repo.get_by_id.assert_called_once_with(1)
        mock_user_repo.update.assert_called_once_with(1, sample_user_entity)

        # Verify entity was modified
        assert sample_user_entity.username == "updateduser"
        assert sample_user_entity.email == "updated@example.com"

    def test_execute_should_only_update_provided_fields(
        self, mock_user_repo, sample_user_entity
    ):
        """
        Given: Update request with only some fields
        When: UpdateUserUseCase.execute() is called
        Then: Should only update provided fields, keep others unchanged
        """
        # Given
        mock_user_repo.get_by_id.return_value = sample_user_entity
        mock_user_repo.update.return_value = sample_user_entity

        update_request = UserUpdateRequest(
            data=UserResourceForUpdate(
                type="users",
                attributes=UserAttributesForUpdate(
                    username="onlynewusername",
                    # email not provided
                ),
            )
        )
        use_case = UpdateUserUseCase(mock_user_repo)

        # When
        use_case.execute(1, update_request)

        # Then
        assert sample_user_entity.username == "onlynewusername"
        assert sample_user_entity.email == "test@example.com"  # Unchanged

    def test_execute_should_return_none_when_user_not_found(
        self, mock_user_repo, sample_update_request
    ):
        """
        Given: A user ID that does not exist
        When: UpdateUserUseCase.execute() is called
        Then: Should return None without calling update
        """
        # Given
        mock_user_repo.get_by_id.return_value = None
        use_case = UpdateUserUseCase(mock_user_repo)

        # When
        result = use_case.execute(999, sample_update_request)

        # Then
        assert result is None
        mock_user_repo.get_by_id.assert_called_once_with(999)
        mock_user_repo.update.assert_not_called()

    def test_execute_should_update_boolean_fields(
        self, mock_user_repo, sample_user_entity
    ):
        """
        Given: Update request with boolean fields (is_active, is_staff, is_superuser)
        When: UpdateUserUseCase.execute() is called
        Then: Should update all boolean fields correctly
        """
        # Given
        mock_user_repo.get_by_id.return_value = sample_user_entity
        mock_user_repo.update.return_value = sample_user_entity

        update_request = UserUpdateRequest(
            data=UserResourceForUpdate(
                type="users",
                attributes=UserAttributesForUpdate(
                    is_active=False,
                    is_staff=True,
                    is_superuser=True,
                ),
            )
        )
        use_case = UpdateUserUseCase(mock_user_repo)

        # When
        use_case.execute(1, update_request)

        # Then
        assert sample_user_entity.is_active is False
        assert sample_user_entity.is_staff is True
        assert sample_user_entity.is_superuser is True


# ============================================================================
# DeleteUserUseCase Tests
# ============================================================================


class TestDeleteUserUseCase:
    """Tests for DeleteUserUseCase."""

    def test_execute_should_return_true_when_user_deleted(self, mock_user_repo):
        """
        Given: A user ID that exists
        When: DeleteUserUseCase.execute() is called
        Then: Should call repository.delete() and return True
        """
        # Given
        mock_user_repo.delete.return_value = True
        use_case = DeleteUserUseCase(mock_user_repo)

        # When
        result = use_case.execute(1)

        # Then
        assert result is True
        mock_user_repo.delete.assert_called_once_with(1)

    def test_execute_should_return_false_when_user_not_found(self, mock_user_repo):
        """
        Given: A user ID that does not exist
        When: DeleteUserUseCase.execute() is called
        Then: Should return False
        """
        # Given
        mock_user_repo.delete.return_value = False
        use_case = DeleteUserUseCase(mock_user_repo)

        # When
        result = use_case.execute(999)

        # Then
        assert result is False
        mock_user_repo.delete.assert_called_once_with(999)
