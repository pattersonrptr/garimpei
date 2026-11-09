import logging
from collections.abc import Iterable
from dataclasses import dataclass, field

from src.collectors.ports import (
    OfferSink,
    OfferSource,
    StoreBlockedError,
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
