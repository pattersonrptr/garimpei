"""Saved searches' use cases, with in-memory fakes for the repository ports.

Only the use cases that decide something are tested here; creating and
listing pass straight to the repositories and stay covered by the e2e and
characterization tests.
"""

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta

import pytest

from src.app.searches.entities import SavedSearch, SearchRun
from src.app.searches.use_cases import (
    DeleteSavedSearchUseCase,
    GetLatestSearchRunUseCase,
    GetSavedSearchesOfUserUseCase,
    GetSavedSearchUseCase,
    GetSearchRunUseCase,
    SavedSearchChanges,
    SavedSearchInUseError,
    SavedSearchNotFoundError,
    SearchRunChanges,
    SearchRunNotFoundError,
    UpdateSavedSearchUseCase,
    UpdateSearchRunUseCase,
)
from src.tests.unit.searches.fakes import (
    FakeSavedSearches,
    FakeSearchAlerts,
    FakeSearchRuns,
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

    def test_a_search_alerts_still_use_cannot_be_deleted(self):
        searches = FakeSavedSearches(DOM_CASMURRO)
        alerts = FakeSearchAlerts({1: [10, 20]})

        with pytest.raises(SavedSearchInUseError) as in_use:
            DeleteSavedSearchUseCase(searches, alerts).execute(1)

        assert in_use.value.alert_count == 2
        assert searches.get_by_id(1) == DOM_CASMURRO

    def test_a_search_no_alert_uses_is_deleted(self):
        searches = FakeSavedSearches(DOM_CASMURRO)

        DeleteSavedSearchUseCase(searches, FakeSearchAlerts({2: [10]})).execute(1)

        assert searches.get_by_id(1) is None


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
