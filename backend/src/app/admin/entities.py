"""The admin summary: the platform's numbers at a glance."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Counts:
    total: int
    active: int


@dataclass(frozen=True, kw_only=True)
class RecentRun:
    """One run of a saved search, as the admin sees it."""

    id: int
    search_id: int
    status: str
    results_count: int | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True)
class ScraperStats:
    recent_total: int
    success_count: int
    failed_count: int

    @classmethod
    def of(cls, runs: Sequence[RecentRun]) -> "ScraperStats":
        """Successes and failures among the runs; any other status (a run
        still going) counts only in the total."""
        return cls(
            recent_total=len(runs),
            success_count=sum(1 for r in runs if r.status == "success"),
            failed_count=sum(1 for r in runs if r.status == "failed"),
        )


@dataclass(frozen=True, kw_only=True)
class AdminSummary:
    users: Counts
    alerts: Counts
    products: int
    stores: Counts
    recent_runs: list[RecentRun]
    scraper_stats: ScraperStats
