"""The PriceAlertChecks catalog's controllers call after a product changes.

Catalog does not know which module implements its ``PriceAlertChecks`` port;
the composition root (``src/app/composition.py``) registers a factory at
start-up, and each request gets checks bound to its database session and
e-mail service.
"""

from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from src.app.catalog.ports import PriceAlertChecks
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.services.email_service import get_email_service
from src.app.interfaces.services.email_service import EmailServiceInterface

PriceAlertChecksFactory = Callable[[Session, EmailServiceInterface], PriceAlertChecks]

_factory: PriceAlertChecksFactory | None = None


def use_price_alert_checks(factory: PriceAlertChecksFactory) -> None:
    """Register the factory (called once by the composition root)."""
    global _factory
    _factory = factory


def get_price_alert_checks(
    db: Session = Depends(get_db),
    email_service: EmailServiceInterface = Depends(get_email_service),
) -> PriceAlertChecks:
    """FastAPI dependency: the registered checks for this request."""
    if _factory is None:
        raise RuntimeError(
            "No PriceAlertChecks registered; src/app/composition.py compose() "
            "must run at start-up"
        )
    return _factory(db, email_service)
