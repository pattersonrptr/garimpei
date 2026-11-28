"""The admin summary (admin module plan, slice 2).

`GetAdminSummaryUseCase` gathers the platform's numbers through admin's own
`PlatformStats` port; the fake below stands in for the other modules.
"""

from datetime import datetime

from src.app.admin.entities import Counts, RecentRun, ScraperStats
from src.app.admin.ports import PlatformStats
from src.app.admin.use_cases import GetAdminSummaryUseCase

START = datetime(2026, 1, 1, 12, 0, 0)


def run(run_id: int, status: str) -> RecentRun:
    return RecentRun(
        id=run_id,
        search_id=7,
        status=status,
        results_count=None,
        error_message=None,
        started_at=START,
        finished_at=None,
    )


class FakePlatformStats(PlatformStats):
    def __init__(self, runs: list[RecentRun] | None = None):
        self.runs = runs or []
        self.asked_runs: int | None = None

    def users(self) -> Counts:
        return Counts(total=5, active=4)

    def alerts(self) -> Counts:
        return Counts(total=3, active=2)

    def products(self) -> int:
        return 40

    def stores(self) -> Counts:
        return Counts(total=6, active=5)

    def recent_runs(self, limit: int) -> list[RecentRun]:
        self.asked_runs = limit
        return self.runs[:limit]


def test_the_summary_has_the_counts_of_each_module():
    summary = GetAdminSummaryUseCase(FakePlatformStats()).execute()

    assert summary.users == Counts(total=5, active=4)
    assert summary.alerts == Counts(total=3, active=2)
    assert summary.products == 40
    assert summary.stores == Counts(total=6, active=5)


def test_the_summary_shows_the_latest_20_runs():
    runs = [run(i, "success") for i in range(25, 0, -1)]
    stats = FakePlatformStats(runs)

    summary = GetAdminSummaryUseCase(stats).execute()

    assert stats.asked_runs == 20
    assert summary.recent_runs == runs[:20]


def test_scraper_stats_count_successes_and_failures_among_the_recent_runs():
    runs = [
        run(4, "running"),
        run(3, "failed"),
        run(2, "success"),
        run(1, "success"),
    ]

    summary = GetAdminSummaryUseCase(FakePlatformStats(runs)).execute()

    assert summary.scraper_stats == ScraperStats(
        recent_total=4, success_count=2, failed_count=1
    )


def test_scraper_stats_are_zero_without_runs():
    summary = GetAdminSummaryUseCase(FakePlatformStats()).execute()

    assert summary.recent_runs == []
    assert summary.scraper_stats == ScraperStats(
        recent_total=0, success_count=0, failed_count=0
    )
