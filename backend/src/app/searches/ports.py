"""Saved searches' ports: what its use cases need from storage and other modules."""

from abc import ABC, abstractmethod

from src.app.searches.entities import RunLimits, SavedSearch, SearchRun


class SavedSearchRepositoryInterface(ABC):
    """Data access for saved searches (search configs)."""

    @abstractmethod
    def create(self, search_config: SavedSearch) -> SavedSearch:
        """Persist a new search config and return it with assigned id."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, search_config_id: int) -> SavedSearch | None:
        """Retrieve a search config by its primary key."""
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> list[SavedSearch]:
        """Return all search configs for a given user."""
        raise NotImplementedError

    @abstractmethod
    def get_by_search_term_and_user_id(
        self, search_term: str, user_id: int
    ) -> SavedSearch | None:
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
    ) -> tuple[list[SavedSearch], int]:
        """Return a paginated list of all search configs and the total count."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self, search_config_id: int, search_config: SavedSearch
    ) -> SavedSearch | None:
        """Update a search config. Returns updated entity or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, search_config_id: int) -> bool:
        """Delete a search config by id. Returns True if deleted, False if not found."""
        raise NotImplementedError


class SearchRunRepositoryInterface(ABC):
    """Data access for the runs of saved searches (search execution logs)."""

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


class SearchAlerts(ABC):
    """The price alerts that use saved searches (owned by alerts)."""

    @abstractmethod
    def user_has_alert(self, user_id: int, search_id: int) -> bool:
        """Does the user have an alert (active or paused) on this search?"""
        raise NotImplementedError

    @abstractmethod
    def count_using(self, search_id: int) -> int:
        """How many alerts (active or paused) use this search."""
        raise NotImplementedError


class RunLimitsReader(ABC):
    """The Run Now limits of a user's plan."""

    @abstractmethod
    def for_user(self, user_id: int) -> RunLimits:
        raise NotImplementedError


class SearchDispatcher(ABC):
    """Sends a saved search to the scrapers."""

    @abstractmethod
    def dispatch(self, search_id: int) -> str:
        """Queue a run of the search; returns the task id."""
        raise NotImplementedError
