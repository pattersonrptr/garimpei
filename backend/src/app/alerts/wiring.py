"""Builds alerts use cases for other modules.

Catalog's controllers evaluate alerts after a product or an offer changes.
They call these factories with the request's database session and e-mail
service, so they never see alerts' adapters (stores, owners, mailer).
"""

from sqlalchemy.orm import Session

from src.app.alerts.persistence.listings import CatalogListings
from src.app.alerts.persistence.mailer import EmailServiceMailer
from src.app.alerts.persistence.owners import UserAccountOwners
from src.app.alerts.persistence.repositories import (
    NotificationLogRepository,
    PriceAlertRepository,
)
from src.app.alerts.persistence.stores import SourceWebsiteStores
from src.app.alerts.use_cases import (
    EvaluateBookAlertsUseCase,
    EvaluateProductAlertsUseCase,
    OpportunityNotifier,
)
from src.app.infrastructure.repositories.source_website_repository import (
    SourceWebsiteRepository,
)
from src.app.infrastructure.repositories.user_repository import UserRepository
from src.app.interfaces.services.email_service import EmailServiceInterface


def evaluate_book_alerts(
    db: Session, email_service: EmailServiceInterface
) -> EvaluateBookAlertsUseCase:
    """Book alerts, checked right after an offer for the book comes in."""
    alerts = PriceAlertRepository(db)
    return EvaluateBookAlertsUseCase(
        listings=CatalogListings(db),
        price_alert_repo=alerts,
        stores=SourceWebsiteStores(SourceWebsiteRepository(db)),
        notifier=OpportunityNotifier(
            NotificationLogRepository(db),
            UserAccountOwners(UserRepository(db)),
            alerts,
            EmailServiceMailer(email_service),
        ),
    )


def evaluate_product_alerts(
    db: Session, email_service: EmailServiceInterface
) -> EvaluateProductAlertsUseCase:
    """Active alerts checked against one product (staff endpoint)."""
    return EvaluateProductAlertsUseCase(
        listings=CatalogListings(db),
        price_alert_repo=PriceAlertRepository(db),
        notification_log_repo=NotificationLogRepository(db),
        owners=UserAccountOwners(UserRepository(db)),
        stores=SourceWebsiteStores(SourceWebsiteRepository(db)),
        mailer=EmailServiceMailer(email_service),
    )
