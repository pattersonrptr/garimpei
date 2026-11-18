from abc import ABC, abstractmethod

from src.app.searches.entities import SearchRun


class SearchExecutionLogRepositoryInterface(ABC):
    """Abstract interface for SearchExecutionLog data access."""

    @abstractmethod
    def create(self, search_execution_log: SearchRun) -> SearchRun:
        """Persist a new search execution log and return it with assigned id."""
        ...

    @abstractmethod
    def update(self, search_execution_log_id: int, changes: dict) -> SearchRun | None:
        """Apply field changes to a log; returns None if it does not exist."""
        ...

    @abstractmethod
    def get_by_id(self, search_execution_log_id: int) -> SearchRun | None:
        """Retrieve a search execution log by its primary key."""
        ...

    @abstractmethod
    def get_by_search_config_id(self, search_config_id: int) -> list[SearchRun]:
        """Return all logs for a given search config, ordered by started_at desc."""
        ...

    @abstractmethod
    def get_latest_by_search_config_id(self, search_config_id: int) -> SearchRun | None:
        """Return the most recent log for a given search config, or None."""
        ...

    @abstractmethod
    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[SearchRun], int]:
        """Return a paginated list of all search execution logs and the total count."""
        ...

    @abstractmethod
    def delete(self, search_execution_log_id: int) -> bool:
        """Delete a log by id. Returns True if deleted, False if not found."""
        ...
