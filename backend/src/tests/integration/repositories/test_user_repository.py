"""
Integration tests for UserRepository.

Tests Repository + Database interactions with real SQLAlchemy operations.
Uses SQLite in-memory for fast, isolated tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.persistence.repositories import UserRepository
from src.app.alerts.persistence.models import PriceAlert
from src.app.infrastructure.database_config import Base

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def test_db():
    """
    Creates an in-memory SQLite database for each test.
    Ensures complete isolation between tests.
    """
    # Create in-memory SQLite engine
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    # Cleanup
    session.close()
    engine.dispose()


@pytest.fixture
def user_repository(test_db):
    """UserRepository with test database session."""
    return UserRepository(test_db)


@pytest.fixture
def sample_user_entity():
    """Sample user entity for testing."""
    return UserEntity(
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$hashed_password_here",
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )


# ============================================================================
# Create Tests
# ============================================================================


class TestUserRepositoryCreate:
    """Tests for UserRepository.create()."""

    def test_create_user_should_persist_to_database(
        self, user_repository, sample_user_entity
    ):
        """
        Given: Valid user entity
        When: repository.create() is called
        Then: Should persist user to database with generated ID and timestamps
        """
        # When
        created_user = user_repository.create(sample_user_entity)

        # Then
        assert created_user.id is not None
        assert created_user.username == "testuser"
        assert created_user.email == "test@example.com"
        assert created_user.hashed_password == "$2b$12$hashed_password_here"
        assert created_user.created_at is not None
        assert created_user.updated_at is not None

        # Verify: Fetch from database
        found_user = user_repository.get_by_id(created_user.id)
        assert found_user is not None
        assert found_user.username == "testuser"

    def test_create_user_with_duplicate_username_should_raise_error(
        self, user_repository, sample_user_entity
    ):
        """
        Given: User with username already exists in database
        When: repository.create() is called with duplicate username
        Then: Should raise IntegrityError (UNIQUE constraint violation)
        """
        # Given: Create first user
        user_repository.create(sample_user_entity)

        # When/Then: Try to create user with same username
        duplicate_user = UserEntity(
            username="testuser",  # Same username
            email="different@example.com",  # Different email
            hashed_password="$2b$12$different_hash",
        )

        with pytest.raises(IntegrityError):
            user_repository.create(duplicate_user)

    def test_create_user_with_duplicate_email_should_raise_error(
        self, user_repository, sample_user_entity
    ):
        """
        Given: User with email already exists in database
        When: repository.create() is called with duplicate email
        Then: Should raise IntegrityError (UNIQUE constraint violation)
        """
        # Given: Create first user
        user_repository.create(sample_user_entity)

        # When/Then: Try to create user with same email
        duplicate_user = UserEntity(
            username="differentuser",  # Different username
            email="test@example.com",  # Same email
            hashed_password="$2b$12$different_hash",
        )

        with pytest.raises(IntegrityError):
            user_repository.create(duplicate_user)

    def test_create_user_should_use_default_values(self, user_repository):
        """
        Given: User entity without optional fields
        When: repository.create() is called
        Then: Should use default values (is_active=True, is_staff=False, etc.)
        """
        # Given
        minimal_user = UserEntity(
            username="minimaluser",
            email="minimal@example.com",
            hashed_password="$2b$12$hash",
        )

        # When
        created_user = user_repository.create(minimal_user)

        # Then
        assert created_user.is_active is True
        assert created_user.is_staff is False
        assert created_user.is_superuser is False


# ============================================================================
# Read Tests
# ============================================================================


class TestUserRepositoryRead:
    """Tests for UserRepository read operations."""

    def test_get_by_id_should_return_user(self, user_repository, sample_user_entity):
        """
        Given: User exists in database
        When: repository.get_by_id() is called
        Then: Should return correct user entity
        """
        # Given
        created_user = user_repository.create(sample_user_entity)

        # When
        found_user = user_repository.get_by_id(created_user.id)

        # Then
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == "testuser"
        assert found_user.email == "test@example.com"

    def test_get_by_id_nonexistent_should_return_none(self, user_repository):
        """
        Given: User ID does not exist in database
        When: repository.get_by_id() is called
        Then: Should return None
        """
        # When
        found_user = user_repository.get_by_id(999)

        # Then
        assert found_user is None

    def test_get_by_username_should_return_user(
        self, user_repository, sample_user_entity
    ):
        """
        Given: User exists in database
        When: repository.get_by_username() is called
        Then: Should return correct user entity
        """
        # Given
        created_user = user_repository.create(sample_user_entity)

        # When
        found_user = user_repository.get_by_username("testuser")

        # Then
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == "testuser"

    def test_get_by_username_nonexistent_should_return_none(self, user_repository):
        """
        Given: Username does not exist in database
        When: repository.get_by_username() is called
        Then: Should return None
        """
        # When
        found_user = user_repository.get_by_username("nonexistent")

        # Then
        assert found_user is None

    def test_get_by_email_should_return_user(self, user_repository, sample_user_entity):
        """
        Given: User exists in database
        When: repository.get_by_email() is called
        Then: Should return correct user entity
        """
        # Given
        created_user = user_repository.create(sample_user_entity)

        # When
        found_user = user_repository.get_by_email("test@example.com")

        # Then
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "test@example.com"

    def test_get_by_email_nonexistent_should_return_none(self, user_repository):
        """
        Given: Email does not exist in database
        When: repository.get_by_email() is called
        Then: Should return None
        """
        # When
        found_user = user_repository.get_by_email("nonexistent@example.com")

        # Then
        assert found_user is None

    def test_get_all_should_return_all_users(self, user_repository):
        """
        Given: Multiple users in database
        When: repository.get_all() is called
        Then: Should return list of all users
        """
        # Given: Create 3 users
        for i in range(3):
            user = UserEntity(
                username=f"user{i}",
                email=f"user{i}@example.com",
                hashed_password="$2b$12$hash",
            )
            user_repository.create(user)

        # When
        all_users = user_repository.get_all()

        # Then
        assert len(all_users) == 3
        assert all_users[0].username == "user0"
        assert all_users[1].username == "user1"
        assert all_users[2].username == "user2"

    def test_get_all_empty_database_should_return_empty_list(self, user_repository):
        """
        Given: No users in database
        When: repository.get_all() is called
        Then: Should return empty list
        """
        # When
        all_users = user_repository.get_all()

        # Then
        assert all_users == []


# ============================================================================
# Update Tests
# ============================================================================


class TestUserRepositoryUpdate:
    """Tests for UserRepository.update()."""

    def test_update_user_should_persist_changes(
        self, user_repository, sample_user_entity
    ):
        """
        Given: Existing user in database
        When: repository.update() is called with modified data
        Then: Should persist changes to database and update updated_at
        """
        # Given: Create user
        created_user = user_repository.create(sample_user_entity)
        original_updated_at = created_user.updated_at

        # When: Update user
        created_user.username = "updated_username"
        created_user.email = "updated@example.com"
        created_user.is_staff = True

        updated_user = user_repository.update(created_user.id, created_user)

        # Then
        assert updated_user is not None
        assert updated_user.username == "updated_username"
        assert updated_user.email == "updated@example.com"
        assert updated_user.is_staff is True
        assert updated_user.updated_at > original_updated_at

        # Verify: Fetch from database
        found_user = user_repository.get_by_id(created_user.id)
        assert found_user.username == "updated_username"
        assert found_user.email == "updated@example.com"

    def test_update_nonexistent_user_should_return_none(self, user_repository):
        """
        Given: User ID does not exist in database
        When: repository.update() is called
        Then: Should return None
        """
        # Given
        nonexistent_user = UserEntity(
            id=999,
            username="ghost",
            email="ghost@example.com",
            hashed_password="$2b$12$hash",
        )

        # When
        result = user_repository.update(999, nonexistent_user)

        # Then
        assert result is None

    def test_update_with_duplicate_username_should_raise_error(self, user_repository):
        """
        Given: Two users in database
        When: repository.update() tries to change username to existing one
        Then: Should raise IntegrityError (UNIQUE constraint violation)
        """
        # Given: Create two users
        user1 = UserEntity(
            username="user1",
            email="user1@example.com",
            hashed_password="$2b$12$hash1",
        )
        user2 = UserEntity(
            username="user2",
            email="user2@example.com",
            hashed_password="$2b$12$hash2",
        )
        user_repository.create(user1)
        created_user2 = user_repository.create(user2)

        # When/Then: Try to update user2's username to user1's username
        created_user2.username = "user1"  # Duplicate!

        with pytest.raises(IntegrityError):
            user_repository.update(created_user2.id, created_user2)


# ============================================================================
# Delete Tests
# ============================================================================


class TestUserRepositoryDelete:
    """Tests for UserRepository.delete()."""

    def test_delete_user_should_remove_from_database(
        self, user_repository, sample_user_entity
    ):
        """
        Given: User exists in database
        When: repository.delete() is called
        Then: Should remove user from database and return True
        """
        # Given
        created_user = user_repository.create(sample_user_entity)

        # When
        result = user_repository.delete(created_user.id)

        # Then
        assert result is True

        # Verify: User should not exist anymore
        found_user = user_repository.get_by_id(created_user.id)
        assert found_user is None

    def test_delete_nonexistent_user_should_return_false(self, user_repository):
        """
        Given: User ID does not exist in database
        When: repository.delete() is called
        Then: Should return False
        """
        # When
        result = user_repository.delete(999)

        # Then
        assert result is False


class TestUserRepositoryDeleteOwnerOfAnAlert:
    """Characterization (Nov 16, 2026): a user who owns an alert is not deleted."""

    def test_deleting_a_user_who_owns_an_alert_fails_and_keeps_the_user(
        self, test_db, user_repository, sample_user_entity
    ):
        user = user_repository.create(sample_user_entity)
        test_db.add(PriceAlert(search_term="duna", max_price=30.0, user_id=user.id))
        test_db.commit()

        with pytest.raises(IntegrityError):
            user_repository.delete(user.id)

        assert user_repository.get_by_id(user.id) is not None
