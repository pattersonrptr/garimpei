"""Saved searches' use cases: the searches and their runs.

They take and return plain data (entities, ids, a SavedSearchChanges or a
SearchRunChanges); a missing search or run is a SavedSearchNotFoundError or
a SearchRunNotFoundError, which the HTTP layer maps to a 404.
"""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, time

from src.app.alerts.ports import PriceAlertRepositoryInterface
from src.app.searches.entities import (
    FINISHED_STATUSES,
    SavedSearch,
    SearchRun,
    SearchRunStatus,
    is_stale_run,
)
from src.app.searches.ports import (
    SavedSearchRepositoryInterface,
    SearchRunRepositoryInterface,
)


class SavedSearchNotFoundError(Exception):
    """No saved search has this id."""


class SearchRunNotFoundError(Exception):
    """No search run has this id."""


class SavedSearchInUseError(Exception):
    """Price alerts still use the saved search, so it cannot be deleted."""

    def __init__(self, alert_count: int):
        super().__init__(f"{alert_count} price alert(s) use this search")
        self.alert_count = alert_count


@dataclass(frozen=True)
class SavedSearchChanges:
    """Fields to change on a saved search; None keeps the current value."""

    search_term: str | None = None
    is_active: bool | None = None
    frequency_days: int | None = None
    preferred_time: time | None = None
    search_metadata: dict | None = None
    source_website_ids: list[int] | None = None


@dataclass(frozen=True)
class SearchRunChanges:
    """What a scraper reports while a run progresses; None keeps the value."""

    status: SearchRunStatus | None = None
    results_count: int | None = None
    listings_found: int | None = None
    listings_checked: int | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Saved searches
# ---------------------------------------------------------------------------


class CreateSavedSearchUseCase:
    def __init__(self, searches: SavedSearchRepositoryInterface):
        self.searches = searches

    def execute(self, search: SavedSearch) -> SavedSearch:
        return self.searches.create(search)


class GetSavedSearchUseCase:
    def __init__(self, searches: SavedSearchRepositoryInterface):
        self.searches = searches

    def execute(self, search_id: int) -> SavedSearch:
        search = self.searches.get_by_id(search_id)
        if search is None:
            raise SavedSearchNotFoundError(search_id)
        return search


class GetSavedSearchesOfUserUseCase:
    def __init__(self, searches: SavedSearchRepositoryInterface):
        self.searches = searches

    def execute(self, user_id: int) -> list[SavedSearch]:
        return self.searches.get_by_user_id(user_id)


class ListSavedSearchesUseCase:
    def __init__(self, searches: SavedSearchRepositoryInterface):
        self.searches = searches

    def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
        user_id: int | None = None,
        search_term: str | None = None,
    ) -> tuple[list[SavedSearch], int]:
        """A page of saved searches (one user's, or all) and the total count."""
        return self.searches.get_all(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            user_id=user_id,
            search_term=search_term,
        )


def _keep(current, new):
    return current if new is None else new


class UpdateSavedSearchUseCase:
    def __init__(self, searches: SavedSearchRepositoryInterface):
        self.searches = searches

    def execute(self, search_id: int, changes: SavedSearchChanges) -> SavedSearch:
        existing = GetSavedSearchUseCase(self.searches).execute(search_id)
        merged = replace(
            existing,
            search_term=_keep(existing.search_term, changes.search_term),
            is_active=_keep(existing.is_active, changes.is_active),
            frequency_days=_keep(existing.frequency_days, changes.frequency_days),
            preferred_time=_keep(existing.preferred_time, changes.preferred_time),
            search_metadata=_keep(existing.search_metadata, changes.search_metadata),
            source_website_ids=_keep(
                existing.source_website_ids, changes.source_website_ids
            ),
        )
        updated = self.searches.update(search_id, merged)
        if updated is None:
            raise SavedSearchNotFoundError(search_id)
        return updated


class DeleteSavedSearchUseCase:
    """Delete a saved search, unless a price alert still uses it."""

    def __init__(
        self,
        searches: SavedSearchRepositoryInterface,
        alerts: PriceAlertRepositoryInterface | None = None,
    ):
        self.searches = searches
        self.alerts = alerts

    def execute(self, search_id: int) -> None:
        if self.alerts is not None:
            in_use = self.alerts.count_by_search_config_id(search_id)
            if in_use:
                raise SavedSearchInUseError(in_use)
        if not self.searches.delete(search_id):
            raise SavedSearchNotFoundError(search_id)


# ---------------------------------------------------------------------------
# Search runs
# ---------------------------------------------------------------------------


class CreateSearchRunUseCase:
    def __init__(self, runs: SearchRunRepositoryInterface):
        self.runs = runs

    def execute(self, run: SearchRun) -> SearchRun:
        return self.runs.create(run)


class GetSearchRunUseCase:
    def __init__(self, runs: SearchRunRepositoryInterface):
        self.runs = runs

    def execute(self, run_id: int) -> SearchRun:
        run = self.runs.get_by_id(run_id)
        if run is None:
            raise SearchRunNotFoundError(run_id)
        return run


class GetRunsOfSearchUseCase:
    def __init__(self, runs: SearchRunRepositoryInterface):
        self.runs = runs

    def execute(self, search_id: int) -> list[SearchRun]:
        """The search's runs, latest first."""
        return self.runs.get_by_search_config_id(search_id)


class ListSearchRunsUseCase:
    def __init__(self, runs: SearchRunRepositoryInterface):
        self.runs = runs

    def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[SearchRun], int]:
        return self.runs.get_all(
            limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
        )


class UpdateSearchRunUseCase:
    """Record the progress or the outcome of a run.

    Closing a run (status success or failed) stamps ``finished_at``.
    """

    def __init__(self, runs: SearchRunRepositoryInterface):
        self.runs = runs

    def execute(
        self, run_id: int, changes: SearchRunChanges, now: datetime | None = None
    ) -> SearchRun:
        fields = {k: v for k, v in vars(changes).items() if v is not None}
        if fields.get("status") in FINISHED_STATUSES:
            fields["finished_at"] = now or datetime.now(UTC)
        updated = self.runs.update(run_id, fields)
        if updated is None:
            raise SearchRunNotFoundError(run_id)
        return updated


class GetLatestSearchRunUseCase:
    """The latest run of a search, closing it first if it was lost."""

    def __init__(self, runs: SearchRunRepositoryInterface):
        self.runs = runs

    def execute(self, search_id: int, now: datetime | None = None) -> SearchRun | None:
        now = now or datetime.now(UTC)
        latest = self.runs.get_latest_by_search_config_id(search_id)
        if latest and latest.id and is_stale_run(latest.status, latest.started_at, now):
            latest = self.runs.update(
                latest.id,
                {
                    "status": "failed",
                    "finished_at": now,
                    "error_message": "The search stopped responding and was closed.",
                },
            )
        return latest
