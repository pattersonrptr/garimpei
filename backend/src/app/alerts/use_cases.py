from datetime import UTC, datetime, timedelta
from math import ceil

from src.app.alerts.entities import NotificationLog as NotificationLogEntity
from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.ports import (
    NotificationLogRepositoryInterface,
    PriceAlertRepositoryInterface,
)
from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.entities import ProductListFilters
from src.app.catalog.ports import (
    PriceHistoryRepositoryInterface,
    ProductRepositoryInterface,
)
from src.app.entities.search_config import SearchConfig as SearchConfigEntity
from src.app.interfaces.repositories.search_config_repository import (
    SearchConfigRepositoryInterface,
)
from src.app.interfaces.repositories.source_website_repository import (
    SourceWebsiteRepositoryInterface,
)
from src.app.interfaces.repositories.user_repository import UserRepositoryInterface
from src.app.interfaces.services.email_service import EmailServiceInterface
from src.config import settings
from src.config.logging_config import get_logger


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


class CreateNotificationLogUseCase:
    """Record a new notification log entry."""

    def __init__(self, notification_log_repo: NotificationLogRepositoryInterface):
        self.notification_log_repo = notification_log_repo

    def execute(self, notification_log: NotificationLogEntity) -> NotificationLogEntity:
        return self.notification_log_repo.create(notification_log)


class GetNotificationLogByIdUseCase:
    """Retrieve a single notification log by its id."""

    def __init__(self, notification_log_repo: NotificationLogRepositoryInterface):
        self.notification_log_repo = notification_log_repo

    def execute(self, notification_log_id: int) -> NotificationLogEntity | None:
        return self.notification_log_repo.get_by_id(notification_log_id)


class GetNotificationLogsByPriceAlertIdUseCase:
    """Retrieve all notification logs for a given price alert."""

    def __init__(self, notification_log_repo: NotificationLogRepositoryInterface):
        self.notification_log_repo = notification_log_repo

    def execute(self, price_alert_id: int) -> list[NotificationLogEntity]:
        return self.notification_log_repo.get_by_price_alert_id(price_alert_id)


class ListNotificationLogsUseCase:
    """List all notification logs with pagination and sorting."""

    def __init__(self, notification_log_repo: NotificationLogRepositoryInterface):
        self.notification_log_repo = notification_log_repo

    def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[NotificationLogEntity], int]:
        return self.notification_log_repo.get_all(
            limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
        )


class DeleteNotificationLogUseCase:
    """Delete a notification log by id."""

    def __init__(self, notification_log_repo: NotificationLogRepositoryInterface):
        self.notification_log_repo = notification_log_repo

    def execute(self, notification_log_id: int) -> bool:
        return self.notification_log_repo.delete(notification_log_id)


class SendPriceAlertNotificationUseCase:
    """Check a price alert for matching products and send email notifications.

    Rate limiting: max 1 email per alert per NOTIFICATION_RATE_LIMIT_MINUTES.

    Returns a list of NotificationLogEntity records created (one per product notified).
    """

    def __init__(
        self,
        price_alert_repo: PriceAlertRepositoryInterface,
        product_repo: ProductRepositoryInterface,
        user_repo: UserRepositoryInterface,
        source_website_repo: SourceWebsiteRepositoryInterface,
        notification_log_repo: NotificationLogRepositoryInterface,
        email_service: EmailServiceInterface,
    ):
        self.price_alert_repo = price_alert_repo
        self.product_repo = product_repo
        self.user_repo = user_repo
        self.source_website_repo = source_website_repo
        self.notification_log_repo = notification_log_repo
        self.email_service = email_service

    def execute(
        self, price_alert_id: int
    ) -> tuple[list[NotificationLogEntity], str | None]:
        """Send notifications for a price alert.

        Returns (logs, error_message):
            - logs: list of created NotificationLog entries
            - error_message: None on success, or description of why it was skipped
        """
        alert = self.price_alert_repo.get_by_id(price_alert_id)
        if not alert:
            return [], "Price alert not found"

        if not alert.is_active:
            return [], "Price alert is inactive"

        # Rate limit check
        rate_limit_minutes = settings.NOTIFICATION_RATE_LIMIT_MINUTES
        since = datetime.now(UTC) - timedelta(minutes=rate_limit_minutes)
        recent_count = self.notification_log_repo.count_since(price_alert_id, since)
        if recent_count > 0:
            return [], (
                f"Rate limited: notification already sent within "
                f"the last {rate_limit_minutes} minutes"
            )

        # Find matching products
        products, total = self.product_repo.search_by_term_and_sources(
            search_term=alert.search_term,
            source_website_ids=alert.source_website_ids,
            max_price=alert.max_price,
            limit=1,  # Send notification for the best match only
            offset=0,
        )

        if not products:
            return [], "No matching products found below max price"

        # Get user info
        user = self.user_repo.get_by_id(alert.user_id)
        if not user:
            return [], "User not found"

        best_product = products[0]

        # Resolve source website name
        source_website = self.source_website_repo.get_by_id(
            best_product.source_website_id
        )
        source_website_name = source_website.name if source_website else "Unknown"

        # Send email
        result = self.email_service.send_price_alert_email(
            to_email=user.email,
            search_term=alert.search_term,
            product_title=best_product.title,
            product_price=best_product.current_price or 0.0,
            max_price=alert.max_price,
            product_url=best_product.url,
            source_website_name=source_website_name,
        )

        # Record notification log
        subject = (
            f"🎯 Oportunidade! {alert.search_term} por "
            f"R$ {best_product.current_price or 0:,.2f} no {source_website_name}"
        )

        log_entry = NotificationLogEntity(
            price_alert_id=price_alert_id,
            user_id=alert.user_id,
            product_id=best_product.id,
            email_to=user.email,
            subject=subject,
            status="sent" if result.success else "failed",
            error_message=result.error_message,
        )
        created_log = self.notification_log_repo.create(log_entry)

        # Update last_triggered_at on the price alert
        alert.last_triggered_at = datetime.now(UTC)
        self.price_alert_repo.update(price_alert_id, alert)

        if not result.success:
            return [created_log], f"Email send failed: {result.error_message}"

        return [created_log], None


logger = get_logger(__name__)


class OpportunityNotifier:
    """Tell one alert's owner about one listing under their max price.

    Shared by the "a product was scraped" flow and the "an alert changed"
    flow. Each alert and product pair is notified at most once (dedup).
    """

    def __init__(
        self,
        notification_log_repo: NotificationLogRepositoryInterface,
        user_repo: UserRepositoryInterface,
        price_alert_repo: PriceAlertRepositoryInterface,
        email_service: EmailServiceInterface,
    ):
        self.notification_log_repo = notification_log_repo
        self.user_repo = user_repo
        self.price_alert_repo = price_alert_repo
        self.email_service = email_service

    def notify(
        self,
        alert: PriceAlertEntity,
        product: ProductEntity,
        current_price: float,
        source_website_name: str,
    ) -> NotificationLogEntity | None:
        """Send the email and log it. Returns None when skipped."""
        alert_id = alert.id
        product_id = product.id
        if alert_id is None or alert.user_id is None or product_id is None:
            return None

        if self.notification_log_repo.exists_for_alert_and_product(
            price_alert_id=alert_id,
            product_id=product_id,
        ):
            logger.debug(
                "Skipping alert %s for product %s: already notified",
                alert_id,
                product_id,
            )
            return None

        user = self.user_repo.get_by_id(alert.user_id)
        if not user:
            logger.warning(
                "User %s not found for alert %s, skipping", alert.user_id, alert_id
            )
            return None

        result = self.email_service.send_price_alert_email(
            to_email=user.email,
            search_term=alert.search_term,
            product_title=product.title,
            product_price=current_price,
            max_price=alert.max_price,
            product_url=product.url,
            source_website_name=source_website_name,
        )

        subject = (
            f"🎯 Oportunidade! {alert.search_term} por "
            f"R$ {current_price:,.2f} no {source_website_name}"
        )
        created_log = self.notification_log_repo.create(
            NotificationLogEntity(
                price_alert_id=alert_id,
                user_id=alert.user_id,
                product_id=product_id,
                email_to=user.email,
                subject=subject,
                status="sent" if result.success else "failed",
                error_message=result.error_message,
            )
        )

        if result.success:
            alert.last_triggered_at = datetime.now(UTC)
            self.price_alert_repo.update(alert_id, alert)
            logger.info(
                "Notification sent for alert %s -> product %s (user: %s)",
                alert_id,
                product_id,
                user.email,
            )
        else:
            logger.warning(
                "Email failed for alert %s -> product %s: %s",
                alert_id,
                product_id,
                result.error_message,
            )
        return created_log


class EvaluateProductAlertsUseCase:
    """Evaluate all active price alerts against a specific product.

    Given a product_id:
    1. Load the product and its latest price.
    2. Find all active PriceAlerts whose search_term matches the product title,
       whose source_website_ids include the product's source, and whose
       max_price >= the product's current price.
    3. For each matching alert, skip if a notification was already sent for
       this exact product + alert pair (dedup).
    4. Send an email notification and create a NotificationLog entry.

    Returns (notifications_sent: list[NotificationLogEntity], skipped: int, error: str | None).
    """

    def __init__(
        self,
        product_repo: ProductRepositoryInterface,
        price_history_repo: PriceHistoryRepositoryInterface,
        price_alert_repo: PriceAlertRepositoryInterface,
        notification_log_repo: NotificationLogRepositoryInterface,
        user_repo: UserRepositoryInterface,
        source_website_repo: SourceWebsiteRepositoryInterface,
        email_service: EmailServiceInterface,
    ):
        self.product_repo = product_repo
        self.price_history_repo = price_history_repo
        self.price_alert_repo = price_alert_repo
        self.notification_log_repo = notification_log_repo
        self.user_repo = user_repo
        self.source_website_repo = source_website_repo
        self.email_service = email_service

    def execute(
        self, product_id: int
    ) -> tuple[list[NotificationLogEntity], int, str | None]:
        """Run the evaluation.

        Returns:
            (sent_logs, skipped_count, error_message)
            - sent_logs: list of NotificationLog entries created
            - skipped_count: number of alerts skipped (dedup)
            - error_message: None on success, or reason for early exit
        """
        # 1. Load product
        product = self.product_repo.get_by_id(product_id)
        if not product:
            return [], 0, "Product not found"

        # 2. Get latest price
        latest_price_record = self.price_history_repo.get_latest_by_product_id(
            product_id
        )
        if not latest_price_record:
            return [], 0, "Product has no price history"

        current_price = latest_price_record.price

        # 3. Find matching alerts
        matching_alerts = self.price_alert_repo.find_matching_alerts_for_product(
            product_title=product.title,
            source_website_id=product.source_website_id,
            current_price=current_price,
        )

        if not matching_alerts:
            return [], 0, "No matching alerts found"

        # Resolve source website name once
        source_website = self.source_website_repo.get_by_id(product.source_website_id)
        source_website_name = source_website.name if source_website else "Unknown"

        notifier = OpportunityNotifier(
            self.notification_log_repo,
            self.user_repo,
            self.price_alert_repo,
            self.email_service,
        )
        sent_logs: list[NotificationLogEntity] = []
        skipped = 0
        for alert in matching_alerts:
            log = notifier.notify(alert, product, current_price, source_website_name)
            if log is None:
                skipped += 1
            elif log.status == "sent":
                sent_logs.append(log)

        return sent_logs, skipped, None


class NotifyAlertOpportunitiesUseCase:
    """When an alert is created or changed, check the listings already collected.

    Without this, raising an alert's max price (or creating an alert for
    something already in the catalog) found nothing until the next scrape.
    Paused alerts send nothing.
    """

    MAX_LISTINGS = 50

    def __init__(
        self,
        product_repo: ProductRepositoryInterface,
        price_alert_repo: PriceAlertRepositoryInterface,
        notification_log_repo: NotificationLogRepositoryInterface,
        user_repo: UserRepositoryInterface,
        source_website_repo: SourceWebsiteRepositoryInterface,
        email_service: EmailServiceInterface,
    ):
        self.product_repo = product_repo
        self.source_website_repo = source_website_repo
        self.notifier = OpportunityNotifier(
            notification_log_repo, user_repo, price_alert_repo, email_service
        )

    def execute(self, alert: PriceAlertEntity) -> list[NotificationLogEntity]:
        if not alert.is_active or alert.id is None:
            return []
        products, _ = self.product_repo.get_all(
            limit=self.MAX_LISTINGS,
            filters=ProductListFilters(
                matching_alert_id=alert.id, opportunities_only=True
            ),
        )
        site_names: dict[int, str] = {}
        sent: list[NotificationLogEntity] = []
        for product in products:
            if product.current_price is None:
                continue
            site_id = product.source_website_id
            if site_id not in site_names:
                site = self.source_website_repo.get_by_id(site_id)
                site_names[site_id] = site.name if site else "Unknown"
            log = self.notifier.notify(
                alert, product, product.current_price, site_names[site_id]
            )
            if log is not None and log.status == "sent":
                sent.append(log)
        return sent
