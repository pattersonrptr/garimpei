"""Rules about search runs (pure domain logic, no framework imports).

A run is one "search on the marketplaces" for a search config, recorded as a
single SearchExecutionLog that the scrapers update while they work.
"""

from datetime import UTC, datetime, timedelta

# The scrapers hold a 30-minute lock per search config. A run still open well
# after that was lost (worker restarted, task crashed) and must not block new
# runs forever.
STALE_RUN_AFTER = timedelta(minutes=35)

FINISHED_STATUSES = ("success", "failed")
OPEN_STATUSES = ("pending", "running")


def is_stale_run(status: str, started_at: datetime | None, now: datetime) -> bool:
    """True when a run is still open long after it should have finished."""
    if status not in OPEN_STATUSES or started_at is None:
        return False
    if started_at.tzinfo is None:  # stored as naive UTC
        started_at = started_at.replace(tzinfo=UTC)
    return now - started_at > STALE_RUN_AFTER
