"""Use case: evaluate all active price alerts against a specific product.

After a product is created or updated (with a new price), this use case
finds all matching PriceAlerts and sends notifications — skipping alerts
for which a notification was already sent for the same product (dedup).
"""

from datetime import UTC, datetime

from src.app.entities.notification_log import NotificationLog as NotificationLogEntity
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

        sent_logs: list[NotificationLogEntity] = []
        skipped = 0

        for alert in matching_alerts:
            alert_id = alert.id
            if alert_id is None or alert.user_id is None:
                skipped += 1
                continue

            # 4. Dedup check
            already_notified = self.notification_log_repo.exists_for_alert_and_product(
                price_alert_id=alert_id,
                product_id=product_id,
            )
            if already_notified:
                logger.debug(
                    "Skipping alert %s for product %s: already notified",
                    alert_id,
                    product_id,
                )
                skipped += 1
                continue

            # 5. Get alert owner
            user = self.user_repo.get_by_id(alert.user_id)
            if not user:
                logger.warning(
                    "User %s not found for alert %s, skipping",
                    alert.user_id,
                    alert_id,
                )
                skipped += 1
                continue

            # 6. Send email notification
            result = self.email_service.send_price_alert_email(
                to_email=user.email,
                search_term=alert.search_term,
                product_title=product.title,
                product_price=current_price,
                max_price=alert.max_price,
                product_url=product.url,
                source_website_name=source_website_name,
            )

            # 7. Record notification log
            subject = (
                f"🎯 Oportunidade! {alert.search_term} por "
                f"R$ {current_price:,.2f} no {source_website_name}"
            )

            log_entry = NotificationLogEntity(
                price_alert_id=alert_id,
                user_id=alert.user_id,
                product_id=product_id,
                email_to=user.email,
                subject=subject,
                status="sent" if result.success else "failed",
                error_message=result.error_message,
            )
            created_log = self.notification_log_repo.create(log_entry)

            if result.success:
                sent_logs.append(created_log)
                # Update last_triggered_at on the alert
                alert.last_triggered_at = datetime.now(UTC)
                self.price_alert_repo.update(alert_id, alert)
                logger.info(
                    "Notification sent for alert %s → product %s (user: %s)",
                    alert_id,
                    product_id,
                    user.email,
                )
            else:
                logger.warning(
                    "Email failed for alert %s → product %s: %s",
                    alert_id,
                    product_id,
                    result.error_message,
                )

        return sent_logs, skipped, None
