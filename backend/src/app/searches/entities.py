"""Saved searches and their runs (pure domain, no framework imports).

A run is one "search on the marketplaces" for a saved search, recorded as a
single SearchRun that the scrapers update while they work.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from typing import Literal

SearchRunStatus = Literal["pending", "running", "success", "failed"]

# The scrapers hold a 30-minute lock per search config. A run still open well
# after that was lost (worker restarted, task crashed) and must not block new
# runs forever.
STALE_RUN_AFTER = timedelta(minutes=35)

FINISHED_STATUSES = ("success", "failed")
OPEN_STATUSES = ("pending", "running")


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(kw_only=True)
class SavedSearch:
    """A search the collectors run on a schedule for a user (a search config)."""

    id: int | None = None
    search_term: str
    is_active: bool = True
    frequency_days: int = 1
    preferred_time: time = time(0, 0)
    search_metadata: dict | None = None
    user_id: int | None = None
    source_website_ids: list[int] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)


@dataclass(kw_only=True)
class SearchRun:
    """One run of a saved search (a search execution log)."""

    id: int | None = None
    search_config_id: int
    status: SearchRunStatus = "pending"
    results_count: int | None = None  # listings that matched the search term
    listings_found: int | None = None  # listings the sites returned
    listings_checked: int | None = None  # listings scraped so far
    error_message: str | None = None
    started_at: datetime = field(default_factory=_now)
    finished_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.status not in FINISHED_STATUSES + OPEN_STATUSES:
            raise ValueError(f"Unknown search run status: {self.status!r}")


def is_stale_run(status: str, started_at: datetime | None, now: datetime) -> bool:
    """True when a run is still open long after it should have finished."""
    if status not in OPEN_STATUSES or started_at is None:
        return False
    if started_at.tzinfo is None:  # stored as naive UTC
        started_at = started_at.replace(tzinfo=UTC)
    return now - started_at > STALE_RUN_AFTER
