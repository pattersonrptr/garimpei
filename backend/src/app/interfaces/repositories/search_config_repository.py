from abc import ABC, abstractmethod

from src.app.entities.search_config import SearchConfig as SearchConfigEntity


class SearchConfigRepositoryInterface(ABC):
    """Abstract interface for SearchConfig data access."""

    @abstractmethod
    def create(self, search_config: SearchConfigEntity) -> SearchConfigEntity:
        """Persist a new search config and return it with assigned id."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, search_config_id: int) -> SearchConfigEntity | None:
        """Retrieve a search config by its primary key."""
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> list[SearchConfigEntity]:
        """Return all search configs for a given user."""
        raise NotImplementedError

    @abstractmethod
    def get_by_search_term_and_user_id(
        self, search_term: str, user_id: int
    ) -> SearchConfigEntity | None:
        """Return a search config matching term + user (for uniqueness check)."""
        raise NotImplementedError

    @abstractmethod
    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
        user_id: int | None = None,
        search_term: str | None = None,
    ) -> tuple[list[SearchConfigEntity], int]:
        """Return a paginated list of all search configs and the total count."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self, search_config_id: int, search_config: SearchConfigEntity
    ) -> SearchConfigEntity | None:
        """Update a search config. Returns updated entity or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, search_config_id: int) -> bool:
        """Delete a search config by id. Returns True if deleted, False if not found."""
        raise NotImplementedError
