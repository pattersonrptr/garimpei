from abc import ABC, abstractmethod

from src.app.entities.price_alert import PriceAlert as PriceAlertEntity


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
        - alert.search_term appears in product_title (case-insensitive)
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
