"""Run Now: a user runs one of their saved searches by hand, within their plan.

Staff (the scrapers' service user, admins) run any search without limits.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from src.app.searches.entities import (
    RunLimits,
    SavedSearch,
    SearchRun,
    SearchRunStatus,
)
from src.app.searches.use_cases import (
    RunLimitReachedError,
    RunSearchNowUseCase,
    SavedSearchNotFoundError,
    SearchAlreadyRunningError,
)
from src.tests.unit.searches.fakes import (
    FakeDispatcher,
    FakeRunLimits,
    FakeSearchAlerts,
    FakeSearchRuns,
)

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
OWNER = 10
FREE = RunLimits(plan_name="free", min_frequency_minutes=360, max_sources=2)

SEARCH = SavedSearch(
    id=1, search_term="dom casmurro", user_id=OWNER, source_website_ids=[1, 2]
)


def a_run(minutes_ago: int, status: SearchRunStatus = "success") -> SearchRun:
    return SearchRun(
        id=1,
        search_config_id=1,
        status=status,
        started_at=NOW - timedelta(minutes=minutes_ago),
    )


class World:
    """A user with an alert on SEARCH, on the free plan, and its runs."""

    def __init__(self, *runs: SearchRun, alerts: dict | None = None):
        self.runs = FakeSearchRuns(*runs)
        self.alerts = FakeSearchAlerts({1: [OWNER]} if alerts is None else alerts)
        self.dispatcher = FakeDispatcher()
        self.use_case = RunSearchNowUseCase(
            self.runs, self.alerts, FakeRunLimits(FREE), self.dispatcher
        )

    def run_now(self, search=SEARCH, staff=False) -> str:
        return self.use_case.execute(
            search, user_id=OWNER, user_is_staff=staff, now=NOW
        )


class TestUserRunsTheirSearch:
    def test_a_search_never_run_is_sent_to_the_scrapers(self):
        world = World()

        task_id = world.run_now()

        assert task_id == "task-1"
        assert world.dispatcher.dispatched == [1]

    def test_a_search_without_one_of_the_users_alerts_is_not_found(self):
        world = World(alerts={})

        with pytest.raises(SavedSearchNotFoundError):
            world.run_now()
        assert world.dispatcher.dispatched == []

    def test_more_stores_than_the_plan_allows_is_refused(self):
        world = World()

        with pytest.raises(RunLimitReachedError) as refused:
            world.run_now(replace(SEARCH, source_website_ids=[1, 2, 3]))

        assert refused.value.violation.meta["limit"] == "max_sources"
        assert world.dispatcher.dispatched == []

    def test_a_run_inside_the_plan_interval_is_refused(self):
        world = World(a_run(minutes_ago=100))

        with pytest.raises(RunLimitReachedError) as refused:
            world.run_now()

        assert refused.value.violation.meta == {
            "limit": "manual_run_interval",
            "value": 360,
            "wait_minutes": 261,
            "plan": "free",
        }
        assert world.dispatcher.dispatched == []

    def test_a_run_after_the_plan_interval_is_sent(self):
        world = World(a_run(minutes_ago=400))

        world.run_now()

        assert world.dispatcher.dispatched == [1]

    def test_a_search_still_running_is_not_sent_again(self):
        world = World(a_run(minutes_ago=5, status="running"))

        with pytest.raises(SearchAlreadyRunningError):
            world.run_now()
        assert world.dispatcher.dispatched == []

    def test_the_store_limit_is_checked_before_a_running_search(self):
        world = World(a_run(minutes_ago=5, status="running"))

        with pytest.raises(RunLimitReachedError):
            world.run_now(replace(SEARCH, source_website_ids=[1, 2, 3]))


class TestStaffRunsAnySearch:
    def test_staff_run_a_search_without_alert_or_plan_limits(self):
        world = World(a_run(minutes_ago=10), alerts={})

        world.run_now(replace(SEARCH, source_website_ids=[1, 2, 3]), staff=True)

        assert world.dispatcher.dispatched == [1]

    def test_staff_do_not_send_a_search_still_running(self):
        world = World(a_run(minutes_ago=5, status="running"))

        with pytest.raises(SearchAlreadyRunningError):
            world.run_now(staff=True)

    def test_a_lost_run_is_closed_and_no_longer_blocks(self):
        world = World(a_run(minutes_ago=36, status="running"))

        world.run_now(staff=True)

        assert world.runs.get_by_id(1).status == "failed"
        assert world.dispatcher.dispatched == [1]
