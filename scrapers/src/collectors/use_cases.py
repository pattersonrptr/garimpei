import logging
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from src.collectors.ports import (
    CollectionQueue,
    OfferSink,
    OfferSource,
    StoreBlockedError,
    StoreRunLog,
    StoreUnavailableError,
)

logger = logging.getLogger(__name__)


@dataclass
class CollectionReport:
    sent: int = 0
    not_found: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    blocked: str | None = None  # why the store stopped, if it did
    skipped: list[str] = field(default_factory=list)  # not asked after a block


class CollectOffers:
    """Ask one store for each ISBN and send what it shows to the sink.

    A block stops the store right away; the remaining ISBNs are skipped, not
    retried. A failure on one ISBN is reported and the run goes on.
    """

    def __init__(self, source: OfferSource, sink: OfferSink):
        self.source = source
        self.sink = sink

    def execute(self, isbns: Iterable[str]) -> CollectionReport:
        report = CollectionReport()
        pending = list(isbns)
        for i, isbn in enumerate(pending):
            try:
                offers = self.source.find_offers(isbn)
            except StoreBlockedError as e:
                report.blocked = str(e)
                report.skipped = pending[i + 1 :]
                report.failed.append((isbn, f"blocked: {e}"))
                logger.warning("%s blocked: %s", self.source.store_name, e)
                break
            except StoreUnavailableError as e:
                report.failed.append((isbn, f"store unavailable: {e}"))
                continue
            if not offers:
                report.not_found.append(isbn)
                continue
            for offer in offers:
                try:
                    self.sink.send(self.source.store_name, offer)
                    report.sent += 1
                except Exception as e:  # noqa: BLE001 - one bad send must not stop the run
                    report.failed.append((isbn, f"send failed: {e}"))
        return report


# Posture rule 9: two days blocked in a row pause the store for a week.
PAUSE_AFTER_BLOCKS = timedelta(days=7)
# A run that sends nothing and fails (the store or the backend down) is tried
# again on the next hourly tick, up to this many times a day.
MAX_FAILED_ATTEMPTS_PER_DAY = 3


@dataclass(frozen=True)
class StoreOutcome:
    store_name: str
    status: str  # collected | blocked | paused | failed | already_done | skipped
    report: CollectionReport | None = None
    detail: str = ""


class CollectDaily:
    """Collect every store once a day, the stalest books first.

    Meant to be called often (every hour): a store already collected today, or
    paused, is skipped, so a PC that was off at the usual time catches up when
    it is turned on. A block stops the store for the rest of the day; a second
    day in a row pauses it for a week. A run that sent nothing and only failed
    is not counted as done, so the next call tries again (a few times a day).
    """

    def __init__(
        self,
        sources: Iterable[OfferSource],
        queue: CollectionQueue,
        sink: OfferSink,
        run_log: StoreRunLog,
        today: date,
    ):
        self.sources = list(sources)
        self.queue = queue
        self.sink = sink
        self.run_log = run_log
        self.today = today

    def execute(self) -> list[StoreOutcome]:
        return [self._collect(source) for source in self.sources]

    def _collect(self, source: OfferSource) -> StoreOutcome:
        name = source.store_name
        state = self.run_log.get(name)
        if state.paused_until and self.today < state.paused_until:
            return StoreOutcome(name, "paused", detail=f"until {state.paused_until}")
        if state.last_run == self.today:
            return StoreOutcome(name, "already_done")
        attempts = state.failed_attempts if state.failed_on == self.today else 0
        if attempts >= MAX_FAILED_ATTEMPTS_PER_DAY:
            return StoreOutcome(name, "skipped", detail=f"{attempts} failed attempts")

        try:
            isbns = self.queue.isbns_for(name)
        except Exception as e:  # noqa: BLE001 - the backend is down: try next hour
            logger.warning("%s: could not read the collection queue: %s", name, e)
            return StoreOutcome(name, "failed", detail=f"queue: {e}")

        report = CollectOffers(source, self.sink).execute(isbns)

        if report.blocked:
            pause = state.last_blocked == self.today - timedelta(days=1)
            paused_until = self.today + PAUSE_AFTER_BLOCKS if pause else None
            self.run_log.save(
                name,
                replace(
                    state,
                    last_run=self.today,
                    last_blocked=self.today,
                    paused_until=paused_until,
                ),
            )
            if pause:
                # Decision 11: logs only for now; this is the line to look for.
                logger.error(
                    "%s blocked two days in a row; paused until %s. Check the "
                    "store by hand before it runs again.",
                    name,
                    paused_until,
                )
            return StoreOutcome(name, "blocked", report, report.blocked)

        if report.sent == 0 and report.failed:
            self.run_log.save(
                name,
                replace(state, failed_on=self.today, failed_attempts=attempts + 1),
            )
            return StoreOutcome(
                name, "failed", report, f"attempt {attempts + 1}, nothing sent"
            )

        self.run_log.save(name, replace(state, last_run=self.today, paused_until=None))
        return StoreOutcome(name, "collected", report)
