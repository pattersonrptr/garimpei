from abc import ABC, abstractmethod

from src.app.stores.entities import Store


class SourceWebsiteRepositoryInterface(ABC):
    """
    Interface for SourceWebsite Repository operations.

    Defines the contract for all source website data access operations,
    following the Repository pattern from Domain-Driven Design.
    """

    @abstractmethod
    def create(self, source_website: Store) -> Store:
        """
        Create a new source website in the repository.

        Args:
            source_website: Store with source website data

        Returns:
            Store: Created source website with generated ID

        Raises:
            IntegrityError: If name constraint is violated (duplicate name)
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, source_website_id: int) -> Store | None:
        """
        Retrieve a source website by its unique ID.

        Args:
            source_website_id: The unique identifier of the source website

        Returns:
            Store if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_name(self, name: str) -> Store | None:
        """
        Retrieve a source website by its unique name.

        Args:
            name: The unique name of the source website

        Returns:
            Store if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[Store], int]:
        """
        Retrieve all source websites with pagination and sorting.

        Args:
            limit: Maximum number of source websites to return
            offset: Number of source websites to skip
            sort_by: Field name to sort by
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            Tuple of (list of Store, total count)
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, source_website_id: int, source_website: Store) -> Store | None:
        """
        Update an existing source website's information.

        Args:
            source_website_id: The ID of the source website to update
            source_website: Store with updated data

        Returns:
            Updated Store if found, None otherwise

        Raises:
            IntegrityError: If update violates name uniqueness constraint
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, source_website_id: int) -> bool:
        """
        Delete a source website from the repository.

        Args:
            source_website_id: The ID of the source website to delete

        Returns:
            True if source website was deleted, False if not found
        """
        raise NotImplementedError
