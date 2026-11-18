"""In-memory fakes for saved searches' ports, shared by its unit tests."""

from dataclasses import replace

from src.app.searches.entities import RunLimits, SavedSearch, SearchRun
from src.app.searches.ports import (
    RunLimitsReader,
    SavedSearchRepositoryInterface,
    SearchAlerts,
    SearchDispatcher,
    SearchRunRepositoryInterface,
)


class FakeSavedSearches(SavedSearchRepositoryInterface):
    def __init__(self, *searches: SavedSearch):
        self.rows = {s.id: s for s in searches}

    def create(self, search_config: SavedSearch) -> SavedSearch:
        created = replace(search_config, id=max(self.rows, default=0) + 1)
        self.rows[created.id] = created
        return created

    def get_by_id(self, search_config_id: int) -> SavedSearch | None:
        return self.rows.get(search_config_id)

    def get_by_user_id(self, user_id: int) -> list[SavedSearch]:
        return [s for s in self.rows.values() if s.user_id == user_id]

    def get_by_search_term_and_user_id(
        self, search_term: str, user_id: int
    ) -> SavedSearch | None:
        return next(
            (
                s
                for s in self.rows.values()
                if s.search_term == search_term and s.user_id == user_id
            ),
            None,
        )

    def get_all(
        self,
        limit=10,
        offset=0,
        sort_by=None,
        sort_order=None,
        user_id=None,
        search_term=None,
    ):
        searches = list(self.rows.values())
        return searches[offset : offset + limit], len(searches)

    def update(
        self, search_config_id: int, search_config: SavedSearch
    ) -> SavedSearch | None:
        if search_config_id not in self.rows:
            return None
        self.rows[search_config_id] = search_config
        return search_config

    def delete(self, search_config_id: int) -> bool:
        return self.rows.pop(search_config_id, None) is not None


class FakeSearchRuns(SearchRunRepositoryInterface):
    def __init__(self, *runs: SearchRun):
        self.rows = {r.id: r for r in runs}

    def create(self, search_execution_log: SearchRun) -> SearchRun:
        created = replace(search_execution_log, id=max(self.rows, default=0) + 1)
        self.rows[created.id] = created
        return created

    def update(self, search_execution_log_id: int, changes: dict) -> SearchRun | None:
        if search_execution_log_id not in self.rows:
            return None
        updated = replace(self.rows[search_execution_log_id], **changes)
        self.rows[search_execution_log_id] = updated
        return updated

    def get_by_id(self, search_execution_log_id: int) -> SearchRun | None:
        return self.rows.get(search_execution_log_id)

    def get_by_search_config_id(self, search_config_id: int) -> list[SearchRun]:
        runs = [r for r in self.rows.values() if r.search_config_id == search_config_id]
        return sorted(runs, key=lambda r: r.started_at, reverse=True)

    def get_latest_by_search_config_id(self, search_config_id: int) -> SearchRun | None:
        return next(iter(self.get_by_search_config_id(search_config_id)), None)

    def get_all(self, limit=10, offset=0, sort_by=None, sort_order=None):
        runs = list(self.rows.values())
        return runs[offset : offset + limit], len(runs)

    def delete(self, search_execution_log_id: int) -> bool:
        return self.rows.pop(search_execution_log_id, None) is not None


class FakeSearchAlerts(SearchAlerts):
    """Which users have an alert on which search: {search_id: [user_id, ...]}."""

    def __init__(self, users_by_search: dict[int, list[int]] | None = None):
        self.users_by_search = users_by_search or {}

    def user_has_alert(self, user_id: int, search_id: int) -> bool:
        return user_id in self.users_by_search.get(search_id, [])

    def count_using(self, search_id: int) -> int:
        return len(self.users_by_search.get(search_id, []))


class FakeRunLimits(RunLimitsReader):
    def __init__(self, limits: RunLimits):
        self.limits = limits

    def for_user(self, user_id: int) -> RunLimits:
        return self.limits


class FakeDispatcher(SearchDispatcher):
    def __init__(self):
        self.dispatched: list[int] = []

    def dispatch(self, search_id: int) -> str:
        self.dispatched.append(search_id)
        return f"task-{len(self.dispatched)}"
