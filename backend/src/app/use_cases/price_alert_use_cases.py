from math import ceil

from src.app.entities.price_alert import PriceAlert as PriceAlertEntity
from src.app.entities.product import Product as ProductEntity
from src.app.entities.search_config import SearchConfig as SearchConfigEntity
from src.app.interfaces.repositories.price_alert_repository import (
    PriceAlertRepositoryInterface,
)
from src.app.interfaces.repositories.product_repository import (
    ProductRepositoryInterface,
)
from src.app.interfaces.repositories.search_config_repository import (
    SearchConfigRepositoryInterface,
)


def _find_or_create_search_config(
    search_config_repo: SearchConfigRepositoryInterface,
    search_term: str,
    source_website_ids: list[int],
    user_id: int,
    frequency_minutes: int,
) -> int:
    """Find an existing SearchConfig matching search_term + user, or create a new one.

    Returns the SearchConfig id.
    """
    existing = search_config_repo.get_by_search_term_and_user_id(search_term, user_id)
    if existing:
        # Reactivate if it was deactivated
        if not existing.is_active:
            existing.is_active = True
            existing.source_website_ids = source_website_ids
            existing.frequency_days = max(1, ceil(frequency_minutes / 1440))
            search_config_repo.update(existing.id, existing)
        return existing.id

    # Create a new SearchConfig bound to this search
    new_config = SearchConfigEntity(
        search_term=search_term,
        is_active=True,
        frequency_days=max(1, ceil(frequency_minutes / 1440)),
        user_id=user_id,
        source_website_ids=source_website_ids,
    )
    created = search_config_repo.create(new_config)
    return created.id


def _cleanup_orphaned_search_config(
    price_alert_repo: PriceAlertRepositoryInterface,
    search_config_repo: SearchConfigRepositoryInterface,
    search_config_id: int | None,
) -> None:
    """Deactivate a SearchConfig if no other active PriceAlerts use it."""
    if search_config_id is None:
        return
    active_count = price_alert_repo.count_active_by_search_config_id(search_config_id)
    if active_count == 0:
        config = search_config_repo.get_by_id(search_config_id)
        if config and config.is_active:
            config.is_active = False
            search_config_repo.update(config.id, config)


class CreatePriceAlertUseCase:
    """Create a new price alert for a user, auto-linking a SearchConfig."""

    def __init__(
        self,
        price_alert_repo: PriceAlertRepositoryInterface,
        search_config_repo: SearchConfigRepositoryInterface,
    ):
        self.price_alert_repo = price_alert_repo
        self.search_config_repo = search_config_repo

    def execute(self, price_alert: PriceAlertEntity) -> PriceAlertEntity:
        search_config_id = _find_or_create_search_config(
            self.search_config_repo,
            price_alert.search_term,
            price_alert.source_website_ids,
            price_alert.user_id,
            price_alert.frequency_minutes,
        )
        price_alert.search_config_id = search_config_id
        return self.price_alert_repo.create(price_alert)


class GetPriceAlertByIdUseCase:
    """Retrieve a single price alert by its id."""

    def __init__(self, price_alert_repo: PriceAlertRepositoryInterface):
        self.price_alert_repo = price_alert_repo

    def execute(self, price_alert_id: int) -> PriceAlertEntity | None:
        return self.price_alert_repo.get_by_id(price_alert_id)


class GetPriceAlertsByUserIdUseCase:
    """Retrieve all price alerts for a given user."""

    def __init__(self, price_alert_repo: PriceAlertRepositoryInterface):
        self.price_alert_repo = price_alert_repo

    def execute(self, user_id: int) -> list[PriceAlertEntity]:
        return self.price_alert_repo.get_by_user_id(user_id)


class ListPriceAlertsUseCase:
    """List all price alerts with pagination and sorting."""

    def __init__(self, price_alert_repo: PriceAlertRepositoryInterface):
        self.price_alert_repo = price_alert_repo

    def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
        user_id: int | None = None,
    ) -> tuple[list[PriceAlertEntity], int]:
        return self.price_alert_repo.get_all(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            user_id=user_id,
        )


class UpdatePriceAlertUseCase:
    """Update an existing price alert, handling SearchConfig linking."""

    def __init__(
        self,
        price_alert_repo: PriceAlertRepositoryInterface,
        search_config_repo: SearchConfigRepositoryInterface,
    ):
        self.price_alert_repo = price_alert_repo
        self.search_config_repo = search_config_repo

    def execute(
        self, price_alert_id: int, price_alert: PriceAlertEntity
    ) -> PriceAlertEntity | None:
        existing = self.price_alert_repo.get_by_id(price_alert_id)
        if not existing:
            return None

        old_search_config_id = existing.search_config_id

        # If search_term or source_websites changed, re-link SearchConfig
        term_changed = price_alert.search_term != existing.search_term
        websites_changed = sorted(price_alert.source_website_ids) != sorted(
            existing.source_website_ids
        )

        if term_changed or websites_changed:
            new_config_id = _find_or_create_search_config(
                self.search_config_repo,
                price_alert.search_term,
                price_alert.source_website_ids,
                price_alert.user_id,
                price_alert.frequency_minutes,
            )
            price_alert.search_config_id = new_config_id
        else:
            price_alert.search_config_id = old_search_config_id

        updated = self.price_alert_repo.update(price_alert_id, price_alert)

        # If alert was deactivated or search config changed, cleanup orphan
        was_deactivated = existing.is_active and not price_alert.is_active
        config_changed = price_alert.search_config_id != old_search_config_id

        if old_search_config_id and (was_deactivated or config_changed):
            _cleanup_orphaned_search_config(
                self.price_alert_repo,
                self.search_config_repo,
                old_search_config_id,
            )

        return updated


class DeletePriceAlertUseCase:
    """Soft-delete a price alert, cleaning up orphaned SearchConfig."""

    def __init__(
        self,
        price_alert_repo: PriceAlertRepositoryInterface,
        search_config_repo: SearchConfigRepositoryInterface,
    ):
        self.price_alert_repo = price_alert_repo
        self.search_config_repo = search_config_repo

    def execute(self, price_alert_id: int) -> bool:
        existing = self.price_alert_repo.get_by_id(price_alert_id)
        if not existing:
            return False

        search_config_id = existing.search_config_id
        deleted = self.price_alert_repo.delete(price_alert_id)

        if deleted and search_config_id:
            _cleanup_orphaned_search_config(
                self.price_alert_repo,
                self.search_config_repo,
                search_config_id,
            )

        return deleted


class GetProductsByPriceAlertUseCase:
    """Retrieve products matching a price alert's criteria, sorted by price."""

    def __init__(
        self,
        price_alert_repo: PriceAlertRepositoryInterface,
        product_repo: ProductRepositoryInterface,
    ):
        self.price_alert_repo = price_alert_repo
        self.product_repo = product_repo

    def execute(
        self,
        price_alert_id: int,
        limit: int = 50,
        offset: int = 0,
        filter_by_max_price: bool = True,
    ) -> tuple[PriceAlertEntity | None, list[ProductEntity], int]:
        """Return (alert, products, total) or (None, [], 0) if alert not found."""
        alert = self.price_alert_repo.get_by_id(price_alert_id)
        if not alert:
            return None, [], 0

        max_price = alert.max_price if filter_by_max_price else None

        products, total = self.product_repo.search_by_term_and_sources(
            search_term=alert.search_term,
            source_website_ids=alert.source_website_ids,
            max_price=max_price,
            limit=limit,
            offset=offset,
        )
        return alert, products, total
