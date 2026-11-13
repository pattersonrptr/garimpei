"""Builds alerts use cases from a database session and an e-mail service.

Alerts' own controller and catalog's controllers call these factories with
the request's database session and e-mail service, so they never see
alerts' adapters (listings, stores, owners, mailer, keyword searches).
"""

from sqlalchemy.orm import Session

from src.app.alerts.http.validators import PriceAlertValidator
from src.app.alerts.persistence.book_finder import CatalogBookFinder
from src.app.alerts.persistence.keyword_searches import SearchConfigKeywordSearches
from src.app.alerts.persistence.listings import CatalogListings
from src.app.alerts.persistence.mailer import EmailServiceMailer
from src.app.alerts.persistence.owners import UserAccountOwners
from src.app.alerts.persistence.repositories import (
    NotificationLogRepository,
    PriceAlertRepository,
)
from src.app.alerts.persistence.stores import SourceWebsiteStores
from src.app.alerts.ports import BookFinder
from src.app.alerts.use_cases import (
    CreatePriceAlertUseCase,
    DeletePriceAlertUseCase,
    EvaluateBookAlertsUseCase,
    EvaluateProductAlertsUseCase,
    NotifyAlertOpportunitiesUseCase,
    OpportunityNotifier,
    SendPriceAlertNotificationUseCase,
    UpdatePriceAlertUseCase,
)
from src.app.infrastructure.repositories.search_config_repository import (
    SearchConfigRepository,
)
from src.app.infrastructure.repositories.source_website_repository import (
    SourceWebsiteRepository,
)
from src.app.infrastructure.repositories.user_repository import UserRepository
from src.app.interfaces.services.email_service import EmailServiceInterface


def _stores(db: Session) -> SourceWebsiteStores:
    return SourceWebsiteStores(SourceWebsiteRepository(db))


def _owners(db: Session) -> UserAccountOwners:
    return UserAccountOwners(UserRepository(db))


def _searches(db: Session) -> SearchConfigKeywordSearches:
    return SearchConfigKeywordSearches(SearchConfigRepository(db))


def book_finder(db: Session) -> BookFinder:
    """Finds the catalog's book for an alert's ISBN."""
    return CatalogBookFinder(db)


def price_alert_validator(db: Session) -> PriceAlertValidator:
    """Checks create and update requests against stores and books."""
    return PriceAlertValidator(PriceAlertRepository(db), _stores(db), book_finder(db))


def create_price_alert(db: Session) -> CreatePriceAlertUseCase:
    return CreatePriceAlertUseCase(PriceAlertRepository(db), _searches(db))


def update_price_alert(db: Session) -> UpdatePriceAlertUseCase:
    return UpdatePriceAlertUseCase(PriceAlertRepository(db), _searches(db))


def delete_price_alert(db: Session) -> DeletePriceAlertUseCase:
    return DeletePriceAlertUseCase(PriceAlertRepository(db), _searches(db))


def alert_opportunities(
    db: Session, email_service: EmailServiceInterface
) -> NotifyAlertOpportunitiesUseCase:
    """Collected listings checked right after an alert is created or changed."""
    return NotifyAlertOpportunitiesUseCase(
        listings=CatalogListings(db),
        price_alert_repo=PriceAlertRepository(db),
        notification_log_repo=NotificationLogRepository(db),
        owners=_owners(db),
        stores=_stores(db),
        mailer=EmailServiceMailer(email_service),
    )


def send_price_alert_notification(
    db: Session, email_service: EmailServiceInterface
) -> SendPriceAlertNotificationUseCase:
    """The best match for one alert, e-mailed to its owner (staff endpoint)."""
    return SendPriceAlertNotificationUseCase(
        price_alert_repo=PriceAlertRepository(db),
        listings=CatalogListings(db),
        owners=_owners(db),
        stores=_stores(db),
        notification_log_repo=NotificationLogRepository(db),
        mailer=EmailServiceMailer(email_service),
    )


def evaluate_book_alerts(
    db: Session, email_service: EmailServiceInterface
) -> EvaluateBookAlertsUseCase:
    """Book alerts, checked right after an offer for the book comes in."""
    alerts = PriceAlertRepository(db)
    return EvaluateBookAlertsUseCase(
        listings=CatalogListings(db),
        price_alert_repo=alerts,
        stores=_stores(db),
        notifier=OpportunityNotifier(
            NotificationLogRepository(db),
            _owners(db),
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
        owners=_owners(db),
        stores=_stores(db),
        mailer=EmailServiceMailer(email_service),
    )
