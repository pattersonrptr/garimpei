"""Use case: evaluate all active price alerts against a specific product.

After a product is created or updated (with a new price), this use case
finds all matching PriceAlerts and sends notifications — skipping alerts
for which a notification was already sent for the same product (dedup).
"""

from datetime import UTC, datetime

from src.app.entities.notification_log import NotificationLog as NotificationLogEntity
from src.app.entities.price_alert import PriceAlert as PriceAlertEntity
from src.app.entities.product import Product as ProductEntity
from src.app.entities.product import ProductListFilters
from src.app.interfaces.repositories.notification_log_repository import (
    NotificationLogRepositoryInterface,
)
from src.app.interfaces.repositories.price_alert_repository import (
    PriceAlertRepositoryInterface,
)
from src.app.interfaces.repositories.price_history_repository import (
    PriceHistoryRepositoryInterface,
)
from src.app.interfaces.repositories.product_repository import (
    ProductRepositoryInterface,
)
from src.app.interfaces.repositories.source_website_repository import (
    SourceWebsiteRepositoryInterface,
)
from src.app.interfaces.repositories.user_repository import UserRepositoryInterface
from src.app.interfaces.services.email_service import EmailServiceInterface
from src.config.logging_config import get_logger

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
