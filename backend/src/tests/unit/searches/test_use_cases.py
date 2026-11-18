"""Saved searches' use cases, with in-memory fakes for the repository ports.

Only the use cases that decide something are tested here; creating and
listing pass straight to the repositories and stay covered by the e2e and
characterization tests.
"""

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta

import pytest

from src.app.searches.entities import SavedSearch, SearchRun
from src.app.searches.ports import (
    SavedSearchRepositoryInterface,
    SearchRunRepositoryInterface,
)
from src.app.searches.use_cases import (
    DeleteSavedSearchUseCase,
    GetLatestSearchRunUseCase,
    GetSavedSearchesOfUserUseCase,
    GetSavedSearchUseCase,
    GetSearchRunUseCase,
    SavedSearchChanges,
    SavedSearchNotFoundError,
    SearchRunChanges,
    SearchRunNotFoundError,
    UpdateSavedSearchUseCase,
    UpdateSearchRunUseCase,
)

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)

DOM_CASMURRO = SavedSearch(
    id=1,
    search_term="dom casmurro",
    is_active=False,
    frequency_days=7,
    preferred_time=time(8, 30),
    search_metadata={"isbn": "9788535910663"},
    user_id=10,
    source_website_ids=[1, 2],
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


def a_run(minutes_ago: int, status="running", **fields) -> SearchRun:
    return SearchRun(
        id=fields.pop("id", 1),
        search_config_id=1,
        status=status,
        started_at=NOW - timedelta(minutes=minutes_ago),
        **fields,
    )


class TestGetSavedSearch:
    def test_a_search_is_found_by_id(self):
        searches = FakeSavedSearches(DOM_CASMURRO)

        assert GetSavedSearchUseCase(searches).execute(1) == DOM_CASMURRO

    def test_a_missing_search_is_not_found(self):
        with pytest.raises(SavedSearchNotFoundError):
            GetSavedSearchUseCase(FakeSavedSearches(DOM_CASMURRO)).execute(99)

    def test_a_users_searches_are_only_theirs(self):
        someone_elses = replace(DOM_CASMURRO, id=2, user_id=20)
        searches = FakeSavedSearches(DOM_CASMURRO, someone_elses)

        assert GetSavedSearchesOfUserUseCase(searches).execute(10) == [DOM_CASMURRO]


class TestUpdateSavedSearch:
    def test_an_update_changes_only_the_fields_given(self):
        searches = FakeSavedSearches(DOM_CASMURRO)

        updated = UpdateSavedSearchUseCase(searches).execute(
            1, SavedSearchChanges(preferred_time=time(20, 0))
        )

        assert updated == replace(DOM_CASMURRO, preferred_time=time(20, 0))
        assert searches.get_by_id(1) == updated

    def test_an_update_can_turn_a_search_on_and_change_its_stores(self):
        searches = FakeSavedSearches(DOM_CASMURRO)

        updated = UpdateSavedSearchUseCase(searches).execute(
            1, SavedSearchChanges(is_active=True, source_website_ids=[3])
        )

        assert (updated.is_active, updated.source_website_ids) == (True, [3])
        assert updated.search_term == "dom casmurro"

    def test_an_empty_store_list_clears_the_stores(self):
        searches = FakeSavedSearches(DOM_CASMURRO)

        updated = UpdateSavedSearchUseCase(searches).execute(
            1, SavedSearchChanges(source_website_ids=[])
        )

        assert updated.source_website_ids == []

    def test_updating_a_missing_search_is_not_found(self):
        with pytest.raises(SavedSearchNotFoundError):
            UpdateSavedSearchUseCase(FakeSavedSearches(DOM_CASMURRO)).execute(
                99, SavedSearchChanges(search_term="x")
            )


class TestDeleteSavedSearch:
    def test_a_deleted_search_is_gone(self):
        searches = FakeSavedSearches(DOM_CASMURRO)

        DeleteSavedSearchUseCase(searches).execute(1)

        assert searches.get_by_id(1) is None

    def test_deleting_a_missing_search_is_not_found(self):
        with pytest.raises(SavedSearchNotFoundError):
            DeleteSavedSearchUseCase(FakeSavedSearches(DOM_CASMURRO)).execute(99)


class TestGetSearchRun:
    def test_a_run_is_found_by_id(self):
        run = a_run(minutes_ago=5)

        assert GetSearchRunUseCase(FakeSearchRuns(run)).execute(1) == run

    def test_a_missing_run_is_not_found(self):
        with pytest.raises(SearchRunNotFoundError):
            GetSearchRunUseCase(FakeSearchRuns(a_run(minutes_ago=5))).execute(99)


class TestUpdateSearchRun:
    def test_progress_is_recorded_and_fields_left_out_are_kept(self):
        runs = FakeSearchRuns(a_run(minutes_ago=5, listings_found=40))

        updated = UpdateSearchRunUseCase(runs).execute(
            1, SearchRunChanges(listings_checked=12), now=NOW
        )

        assert (updated.status, updated.listings_found, updated.listings_checked) == (
            "running",
            40,
            12,
        )
        assert updated.finished_at is None

    @pytest.mark.parametrize("status", ["success", "failed"])
    def test_closing_a_run_stamps_when_it_finished(self, status):
        runs = FakeSearchRuns(a_run(minutes_ago=5))

        updated = UpdateSearchRunUseCase(runs).execute(
            1, SearchRunChanges(status=status, results_count=3), now=NOW
        )

        assert (updated.status, updated.results_count) == (status, 3)
        assert updated.finished_at == NOW

    def test_updating_a_missing_run_is_not_found(self):
        with pytest.raises(SearchRunNotFoundError):
            UpdateSearchRunUseCase(FakeSearchRuns()).execute(
                99, SearchRunChanges(status="running"), now=NOW
            )


class TestLatestSearchRun:
    def test_a_search_never_run_has_no_latest_run(self):
        assert GetLatestSearchRunUseCase(FakeSearchRuns()).execute(1, now=NOW) is None

    def test_the_latest_run_is_the_most_recent(self):
        older = a_run(minutes_ago=90, status="success", id=1)
        newer = a_run(minutes_ago=10, status="success", id=2)

        latest = GetLatestSearchRunUseCase(FakeSearchRuns(older, newer)).execute(
            1, now=NOW
        )

        assert latest == newer

    def test_a_run_open_for_more_than_35_minutes_is_closed_as_failed(self):
        runs = FakeSearchRuns(a_run(minutes_ago=36, status="running"))

        latest = GetLatestSearchRunUseCase(runs).execute(1, now=NOW)

        assert latest.status == "failed"
        assert latest.finished_at == NOW
        assert latest.error_message == "The search stopped responding and was closed."
        assert runs.get_by_id(1) == latest

    def test_a_run_open_for_less_than_35_minutes_keeps_running(self):
        run = a_run(minutes_ago=30, status="pending")

        latest = GetLatestSearchRunUseCase(FakeSearchRuns(run)).execute(1, now=NOW)

        assert latest == run

    def test_an_old_finished_run_is_left_as_it_is(self):
        run = a_run(minutes_ago=600, status="success")

        latest = GetLatestSearchRunUseCase(FakeSearchRuns(run)).execute(1, now=NOW)

        assert latest == run
