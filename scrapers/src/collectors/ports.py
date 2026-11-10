from abc import ABC, abstractmethod

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
