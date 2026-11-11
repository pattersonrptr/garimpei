from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from src.collectors.offers import CollectedOffer


class StoreBlockedError(Exception):
    """The store said no: captcha, 403, 429, an empty page, or robots.txt.
    The posture rule is to stop that store for the day, never to work around it."""


class StoreUnavailableError(Exception):
    """The store or the network failed (timeout, 5xx). Worth a retry later."""


class PageFetcher(ABC):
    """Fetches a page's body for a store adapter (the polite HTTP client)."""

    @abstractmethod
    def get(self, url: str) -> str:
        """The body. Raises StoreBlockedError or StoreUnavailableError."""


class OfferSource(ABC):
    """A store that can be asked for a product by its identifier."""

    store_name: str  # the store's slug in the backend, e.g. "estante_virtual"

    @abstractmethod
    def find_offers(self, isbn13: str) -> list[CollectedOffer]:
        """The store's offers for this ISBN; an empty list if it has none."""


class OfferSink(ABC):
    """Where collected offers go (the backend's POST /offers)."""

    @abstractmethod
    def send(self, store_name: str, offer: CollectedOffer) -> None:
        """Deliver one offer. Raises on failure."""


class CollectionQueue(ABC):
    """Which products a store should be asked for, stalest first (the backend's
    GET /offers/collection-queue)."""

    @abstractmethod
    def isbns_for(self, store_name: str) -> list[str]:
        """Every ISBN to look up at this store, the stalest first."""


@dataclass(frozen=True)
class StoreRunState:
    """What the daily collection remembers about a store between runs."""

    last_run: date | None = None  # the day the store's collection was done
    last_blocked: date | None = None  # the last day the store blocked us
    paused_until: date | None = None  # not asked again before this day
    failed_on: date | None = None  # the day of the failed attempts below
    failed_attempts: int = 0


class StoreRunLog(ABC):
    """Keeps each store's StoreRunState across runs (Redis today)."""

    @abstractmethod
    def get(self, store_name: str) -> StoreRunState:
        """The store's state; a blank one if it never ran."""

    @abstractmethod
    def save(self, store_name: str, state: StoreRunState) -> None:
        """Replace the store's state."""
