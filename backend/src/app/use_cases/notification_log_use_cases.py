from datetime import UTC, datetime, timedelta

from src.app.catalog.ports import (
    ProductRepositoryInterface,
)
from src.app.entities.notification_log import NotificationLog as NotificationLogEntity
from src.app.interfaces.repositories.notification_log_repository import (
    NotificationLogRepositoryInterface,
)
from src.app.interfaces.repositories.price_alert_repository import (
    PriceAlertRepositoryInterface,
)
from src.app.interfaces.repositories.source_website_repository import (
    SourceWebsiteRepositoryInterface,
)
from src.app.interfaces.repositories.user_repository import UserRepositoryInterface
from src.app.interfaces.services.email_service import EmailServiceInterface
from src.config import settings


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
