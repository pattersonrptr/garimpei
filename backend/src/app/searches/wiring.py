"""Builds saved searches' use cases from a database session.

The composition point for searches' ports: alerts, billing and the scrapers'
queue are reached through searches-owned adapters.
"""

from sqlalchemy.orm import Session

from src.app.alerts import wiring as alerts_wiring
from src.app.billing import wiring as billing_wiring
from src.app.searches.adapters.alerts import SearchAlertsOverAlerts
from src.app.searches.adapters.dispatcher import CelerySearchDispatcher
from src.app.searches.adapters.plan_limits import RunLimitsOverBilling
from src.app.searches.persistence.repositories import (
    SavedSearchRepository,
    SearchRunRepository,
)
from src.app.searches.use_cases import DeleteSavedSearchUseCase, RunSearchNowUseCase


def _alerts(db: Session) -> SearchAlertsOverAlerts:
    return SearchAlertsOverAlerts(alerts_wiring.price_alerts(db))


def delete_saved_search(db: Session) -> DeleteSavedSearchUseCase:
    return DeleteSavedSearchUseCase(SavedSearchRepository(db), _alerts(db))


def run_search_now(db: Session) -> RunSearchNowUseCase:
    return RunSearchNowUseCase(
        SearchRunRepository(db),
        _alerts(db),
        RunLimitsOverBilling(billing_wiring.user_plan_limits(db)),
        CelerySearchDispatcher(),
    )
