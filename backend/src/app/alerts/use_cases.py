from datetime import UTC, datetime, timedelta
from math import ceil

from src.app.alerts.entities import KeywordSearch, Listing, MyAlert, NoticeHistory
from src.app.alerts.entities import NotificationLog as NotificationLogEntity
from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.notification_text import alert_subject
from src.app.alerts.ports import (
    AlertMailer,
    AlertOwnerReader,
    KeywordSearches,
    Listings,
    NotificationLogRepositoryInterface,
    PriceAlertRepositoryInterface,
    ProductSnapshotReader,
    StoreReader,
)
from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.entities import ProductListFilters
from src.app.catalog.ports import ProductRepositoryInterface
from src.config import settings
from src.config.logging_config import get_logger


def _find_or_create_search_config(
    search_config_repo: KeywordSearches,
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
    new_config = KeywordSearch(
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
    search_config_repo: KeywordSearches,
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
        search_config_repo: KeywordSearches,
    ):
        self.price_alert_repo = price_alert_repo
        self.search_config_repo = search_config_repo

    def execute(self, price_alert: PriceAlertEntity) -> PriceAlertEntity:
        if price_alert.is_book_alert:
            price_alert.search_config_id = None
            return self.price_alert_repo.create(price_alert)
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
        search_config_repo: KeywordSearches,
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

        if existing.is_book_alert:
            price_alert.search_config_id = None
        elif term_changed or websites_changed:
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
        search_config_repo: KeywordSearches,
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
        product_repo: Listings,
        user_repo: AlertOwnerReader,
        source_website_repo: StoreReader,
        notification_log_repo: NotificationLogRepositoryInterface,
        email_service: AlertMailer,
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

        # The best match only: the cheapest listing at or under the max price
        best_product = self.product_repo.cheapest_match(
            search_term=alert.search_term,
            store_ids=alert.source_website_ids,
            max_price=alert.max_price,
        )

        if best_product is None:
            return [], "No matching products found below max price"

        # Get user info
        user = self.user_repo.get_by_id(alert.user_id)
        if not user:
            return [], "User not found"

        # Resolve source website name
        source_website = self.source_website_repo.get_by_id(best_product.store_id)
        source_website_name = source_website.name if source_website else "Unknown"

        # Send email
        result = self.email_service.send_price_alert_email(
            to_email=user.email,
            search_term=alert.search_term,
            product_title=best_product.title,
            product_price=best_product.price or 0.0,
            max_price=alert.max_price,
            product_url=best_product.url,
            source_website_name=source_website_name,
        )

        # Record notification log
        subject = alert_subject(
            alert.search_term, best_product.price or 0.0, source_website_name
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
        user_repo: AlertOwnerReader,
        price_alert_repo: PriceAlertRepositoryInterface,
        email_service: AlertMailer,
    ):
        self.notification_log_repo = notification_log_repo
        self.user_repo = user_repo
        self.price_alert_repo = price_alert_repo
        self.email_service = email_service

    def notify(
        self,
        alert: PriceAlertEntity,
        product: Listing | ProductEntity,
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

        subject = alert_subject(alert.search_term, current_price, source_website_name)
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
        product_repo: Listings,
        price_alert_repo: PriceAlertRepositoryInterface,
        notification_log_repo: NotificationLogRepositoryInterface,
        user_repo: AlertOwnerReader,
        source_website_repo: StoreReader,
        email_service: AlertMailer,
    ):
        self.product_repo = product_repo
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

        # 2. Its latest price
        if product.price is None:
            return [], 0, "Product has no price history"

        current_price = product.price

        # 3. Find matching alerts
        matching_alerts = self.price_alert_repo.find_matching_alerts_for_product(
            product_title=product.title,
            source_website_id=product.store_id,
            current_price=current_price,
        )

        if not matching_alerts:
            return [], 0, "No matching alerts found"

        # Resolve source website name once
        source_website = self.source_website_repo.get_by_id(product.store_id)
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
        user_repo: AlertOwnerReader,
        source_website_repo: StoreReader,
        email_service: AlertMailer,
    ):
        self.product_repo = product_repo
        self.source_website_repo = source_website_repo
        self.notifier = OpportunityNotifier(
            notification_log_repo, user_repo, price_alert_repo, email_service
        )
        self.book_alerts = EvaluateBookAlertsUseCase(
            product_repo, price_alert_repo, source_website_repo, self.notifier
        )

    def execute(self, alert: PriceAlertEntity) -> list[NotificationLogEntity]:
        if not alert.is_active or alert.id is None:
            return []
        if alert.is_book_alert:
            log = self.book_alerts.evaluate_alert(alert)
            return [log] if log is not None and log.status == "sent" else []
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


class EvaluateBookAlertsUseCase:
    """Check a book's alerts against the book's offers (Phase 4c).

    For each active alert on the book: the cheapest offer in stock, in a
    condition the alert wants, at or under its max price, is sent to the
    owner. One e-mail per alert per check; an alert and offer pair is never
    sent twice (``OpportunityNotifier``), so a further drop on the same offer
    sends nothing (known MVP limit).
    """

    MAX_OFFERS = 200

    def __init__(
        self,
        product_repo: ProductRepositoryInterface,
        price_alert_repo: PriceAlertRepositoryInterface,
        source_website_repo: StoreReader,
        notifier: OpportunityNotifier,
    ):
        self.product_repo = product_repo
        self.price_alert_repo = price_alert_repo
        self.source_website_repo = source_website_repo
        self.notifier = notifier

    def execute(self, canonical_product_id: int) -> list[NotificationLogEntity]:
        """Every active alert on the book. Returns the e-mails sent."""
        alerts = self.price_alert_repo.get_active_by_book(canonical_product_id)
        if not alerts:
            return []
        offers = self._offers(canonical_product_id)
        sent = []
        for alert in alerts:
            log = self._notify_best(alert, offers)
            if log is not None and log.status == "sent":
                sent.append(log)
        return sent

    def evaluate_alert(self, alert: PriceAlertEntity) -> NotificationLogEntity | None:
        """One alert (just created or changed)."""
        if not alert.is_active or alert.canonical_product_id is None:
            return None
        return self._notify_best(alert, self._offers(alert.canonical_product_id))

    def _offers(self, canonical_product_id: int) -> list[ProductEntity]:
        offers, _ = self.product_repo.get_all(
            limit=self.MAX_OFFERS,
            filters=ProductListFilters(
                canonical_product_id=canonical_product_id, is_available=True
            ),
        )
        return offers

    def _notify_best(
        self, alert: PriceAlertEntity, offers: list[ProductEntity]
    ) -> NotificationLogEntity | None:
        wanted = [
            offer
            for offer in offers
            if offer.current_price is not None
            and offer.current_price <= alert.max_price
            and offer.is_available is not False
            and alert.accepts_condition(_condition_value(offer.condition))
        ]
        if not wanted:
            return None
        best = min(wanted, key=lambda offer: offer.current_price)
        site = self.source_website_repo.get_by_id(best.source_website_id)
        return self.notifier.notify(
            alert, best, best.current_price, site.name if site else "Unknown"
        )


def _condition_value(condition) -> str:
    return getattr(condition, "value", condition) or ""


class ListMyAlertsUseCase:
    """A user's product alerts with each product today and the e-mails sent.

    Keyword alerts are left out: they no longer show on the user's screens
    (Phase 5). Active alerts first, then the newest.
    """

    def __init__(
        self,
        price_alert_repo: PriceAlertRepositoryInterface,
        products: ProductSnapshotReader,
        notification_log_repo: NotificationLogRepositoryInterface,
    ):
        self.price_alert_repo = price_alert_repo
        self.products = products
        self.notification_log_repo = notification_log_repo

    def execute(self, user_id: int) -> list[MyAlert]:
        alerts = [
            a for a in self.price_alert_repo.get_by_user_id(user_id) if a.is_book_alert
        ]
        if not alerts:
            return []
        alerts.sort(key=lambda a: (not a.is_active, -a.created_at.timestamp()))
        snapshots = self.products.snapshots(
            sorted({a.canonical_product_id for a in alerts if a.canonical_product_id})
        )
        history = self.notification_log_repo.sent_history(
            [a.id for a in alerts if a.id is not None]
        )
        return [
            MyAlert(
                alert=alert,
                product=snapshots.get(alert.canonical_product_id or 0),
                notices=history.get(alert.id or 0, NoticeHistory()),
            )
            for alert in alerts
        ]
