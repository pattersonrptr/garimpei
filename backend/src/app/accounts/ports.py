from abc import ABC, abstractmethod

from src.app.accounts.entities import User as UserEntity


class UserHasDataError(Exception):
    """The user still has data (alerts, notifications, subscription or saved
    searches), so they are kept; deactivate them instead."""


class UserRepositoryInterface(ABC):
    """
    Interface for User Repository operations.

    Defines the contract for all user data access operations,
    following the Repository pattern from Domain-Driven Design.
    """

    @abstractmethod
    def create(self, user: UserEntity) -> UserEntity:
        """
        Create a new user in the repository.

        Args:
            user: UserEntity with user data

        Returns:
            UserEntity: Created user with generated ID

        Raises:
            IntegrityError: If username or email already exists
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: int) -> UserEntity | None:
        """
        Retrieve a user by their unique ID.

        Args:
            user_id: The unique identifier of the user

        Returns:
            UserEntity if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_username(self, username: str) -> UserEntity | None:
        """
        Retrieve a user by their username.

        Args:
            username: The unique username

        Returns:
            UserEntity if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> UserEntity | None:
        """
        Retrieve a user by their email address.

        Args:
            email: The unique email address

        Returns:
            UserEntity if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[UserEntity]:
        """
        Retrieve all users from the repository.

        Returns:
            List of UserEntity objects (may be empty)
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, user_id: int, user: UserEntity) -> UserEntity | None:
        """
        Update an existing user's information.

        Args:
            user_id: The ID of the user to update
            user: UserEntity with updated data (only changed fields)

        Returns:
            Updated UserEntity if user exists, None otherwise

        Raises:
            IntegrityError: If update violates unique constraints
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """
        Delete a user from the repository.

        Args:
            user_id: The ID of the user to delete

        Returns:
            True if user was deleted, False if user not found

        Raises:
            UserHasDataError: When the user still has data; the user is kept
        """
        raise NotImplementedError
