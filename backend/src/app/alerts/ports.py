from abc import ABC, abstractmethod
from datetime import datetime

from src.app.alerts.entities import BookRef, NoticeHistory, ProductSnapshot
from src.app.alerts.entities import NotificationLog as NotificationLogEntity
from src.app.alerts.entities import PriceAlert as PriceAlertEntity


class PriceAlertRepositoryInterface(ABC):
    """Abstract interface for PriceAlert data access."""

    @abstractmethod
    def create(self, price_alert: PriceAlertEntity) -> PriceAlertEntity:
        """Persist a new price alert and return it with assigned id."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, price_alert_id: int) -> PriceAlertEntity | None:
        """Retrieve a price alert by its primary key."""
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> list[PriceAlertEntity]:
        """Return all price alerts for a given user."""
        raise NotImplementedError

    @abstractmethod
    def get_by_search_term_and_user_id(
        self, search_term: str, user_id: int
    ) -> PriceAlertEntity | None:
        """Return a price alert matching term + user (for uniqueness check)."""
        raise NotImplementedError

    @abstractmethod
    def get_by_book_and_user_id(
        self, canonical_product_id: int, user_id: int, condition: str
    ) -> PriceAlertEntity | None:
        """A user's non-deleted alert on a book and condition (uniqueness check)."""
        raise NotImplementedError

    @abstractmethod
    def get_active_by_book(self, canonical_product_id: int) -> list[PriceAlertEntity]:
        """Every active, non-deleted alert on a book."""
        raise NotImplementedError

    @abstractmethod
    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
        user_id: int | None = None,
    ) -> tuple[list[PriceAlertEntity], int]:
        """Return a paginated list of all price alerts and the total count."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self, price_alert_id: int, price_alert: PriceAlertEntity
    ) -> PriceAlertEntity | None:
        """Update a price alert. Returns updated entity or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, price_alert_id: int) -> bool:
        """Delete a price alert by id. Returns True if deleted, False if not found."""
        raise NotImplementedError

    @abstractmethod
    def count_active_by_user_id(self, user_id: int) -> int:
        """Count active, non-deleted price alerts owned by a user."""
        raise NotImplementedError

    @abstractmethod
    def count_by_search_config_id(self, search_config_id: int) -> int:
        """Count non-deleted price alerts (active or paused) using a SearchConfig."""
        raise NotImplementedError

    @abstractmethod
    def count_active_by_search_config_id(self, search_config_id: int) -> int:
        """Count active price alerts that reference a given SearchConfig."""
        raise NotImplementedError

    @abstractmethod
    def find_matching_alerts_for_product(
        self,
        product_title: str,
        source_website_id: int,
        current_price: float,
    ) -> list[PriceAlertEntity]:
        """Find all active price alerts that match a given product.

        A match occurs when:
        - alert.is_active is True
        - alert.search_term appears in product_title (case/accent-insensitive)
        - source_website_id is in alert.source_website_ids
        - current_price <= alert.max_price

        Args:
            product_title: The product title to match against alert search terms.
            source_website_id: The product's source website ID.
            current_price: The product's current price.

        Returns:
            List of matching PriceAlert entities.
        """
        raise NotImplementedError


class BookFinder(ABC):
    """Finds the book a book alert is created for (implemented over the catalog)."""

    @abstractmethod
    def find_by_isbn(self, isbn: str) -> BookRef | None:
        """The catalog's book for an ISBN-10 or ISBN-13; None when unknown or invalid."""
        raise NotImplementedError


class NotificationLogRepositoryInterface(ABC):
    """Abstract interface for NotificationLog data access."""

    @abstractmethod
    def create(self, notification_log: NotificationLogEntity) -> NotificationLogEntity:
        """Persist a new notification log and return it with assigned id."""
        ...

    @abstractmethod
    def get_by_id(self, notification_log_id: int) -> NotificationLogEntity | None:
        """Retrieve a notification log by its primary key."""
        ...

    @abstractmethod
    def get_by_price_alert_id(self, price_alert_id: int) -> list[NotificationLogEntity]:
        """Return all logs for a given price alert, ordered by sent_at desc."""
        ...

    @abstractmethod
    def get_last_sent_for_alert(
        self, price_alert_id: int
    ) -> NotificationLogEntity | None:
        """Return the most recent successfully sent notification for a price alert."""
        ...

    @abstractmethod
    def count_since(self, price_alert_id: int, since: datetime) -> int:
        """Count successfully sent notifications for a price alert since a given time."""
        ...

    @abstractmethod
    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[NotificationLogEntity], int]:
        """Return a paginated list of all notification logs and the total count."""
        ...

    @abstractmethod
    def delete(self, notification_log_id: int) -> bool:
        """Delete a log by id. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    def sent_history(
        self, price_alert_ids: list[int], recent: int = 5
    ) -> dict[int, NoticeHistory]:
        """Per alert: the latest ``recent`` sent e-mails (with the store) and the total."""
        ...

    @abstractmethod
    def exists_for_alert_and_product(
        self, price_alert_id: int, product_id: int
    ) -> bool:
        """Check if a successful notification was already sent for a given alert + product pair.

        Used to prevent duplicate notifications when a product is re-evaluated.

        Args:
            price_alert_id: The price alert ID.
            product_id: The product ID.

        Returns:
            True if a 'sent' notification log exists for this pair, False otherwise.
        """
        ...


class ProductSnapshotReader(ABC):
    """The products "my alerts" shows (implemented over the catalog)."""

    @abstractmethod
    def snapshots(self, product_ids: list[int]) -> dict[int, ProductSnapshot]:
        """Each known product by id; unknown ids are left out."""
        raise NotImplementedError
