"""Bookkeeping for one search run spread over many Celery tasks.

A run ("search this term on these sites") becomes one task per site and one
task per batch of listings. Each of those is a *step*. The run keeps its
counters in a Redis hash so any worker can update them, and the step that
brings ``pending`` to zero closes the run.

Keys expire after a few hours, so a crashed run cannot leave data behind.
"""

import unicodedata

COUNTERS = ("listings_found", "listings_checked", "results_count")


class SearchRun:
    TTL_SECONDS = 4 * 60 * 60

    def __init__(self, redis_client, log_id: int | str):
        self.redis = redis_client
        self.log_id = str(log_id)
        self.key = f"search_run:{self.log_id}"
        self.errors_key = f"{self.key}:errors"

    def start(self, steps: int) -> None:
        """Open the run with ``steps`` pending steps (one per site)."""
        self.redis.hset(
            self.key, mapping={"pending": steps, **dict.fromkeys(COUNTERS, 0)}
        )
        self.redis.expire(self.key, self.TTL_SECONDS)

    def add_steps(self, count: int) -> None:
        if count:
            self.redis.hincrby(self.key, "pending", count)

    def add(self, counter: str, amount: int) -> None:
        if amount:
            self.redis.hincrby(self.key, counter, amount)

    def add_error(self, message: str) -> None:
        self.redis.rpush(self.errors_key, message)
        self.redis.expire(self.errors_key, self.TTL_SECONDS)

    def step_done(self) -> bool:
        """Mark one step finished. True for the step that finished the run."""
        return int(self.redis.hincrby(self.key, "pending", -1)) <= 0

    def snapshot(self) -> dict[str, int]:
        values = self.redis.hgetall(self.key) or {}
        return {name: int(values.get(name, 0) or 0) for name in COUNTERS}

    def errors(self) -> list[str]:
        return list(self.redis.lrange(self.errors_key, 0, -1) or [])

    def clear(self) -> None:
        self.redis.delete(self.key, self.errors_key)


def fold_text(text: str) -> str:
    """Lowercase and strip accents: "Microsserviços" -> "microsservicos".

    Same rule as the backend's text_match.fold_text, so a listing is kept
    exactly when an alert for the same term would match it.
    """
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def title_matches(title: str, search_term: str) -> bool:
    """Does the listing title contain the search term (ignoring case and accents)?"""
    return fold_text(search_term).strip() in fold_text(title)
