"""Builds saved searches' use cases from a database session.

The composition point for searches' ports: alerts, billing, stores and the
scrapers' queue are reached through searches-owned adapters.
"""

from sqlalchemy.orm import Session

from src.app.alerts import wiring as alerts_wiring
from src.app.billing import wiring as billing_wiring
from src.app.searches.adapters.alerts import SearchAlertsOverAlerts
from src.app.searches.adapters.dispatcher import CelerySearchDispatcher
from src.app.searches.adapters.plan_limits import RunLimitsOverBilling
from src.app.searches.adapters.stores import SearchStoresOverStores
from src.app.searches.http.validators import SavedSearchValidator, SearchRunValidator
from src.app.searches.persistence.repositories import (
    SavedSearchRepository,
    SearchRunRepository,
)
from src.app.searches.ports import (
    SavedSearchRepositoryInterface,
    SearchRunRepositoryInterface,
)
from src.app.searches.use_cases import (
    CreateSavedSearchUseCase,
    DeleteSavedSearchUseCase,
    FindSavedSearchByTermUseCase,
    GetSavedSearchUseCase,
    ListSearchRunsUseCase,
    RunSearchNowUseCase,
    UpdateSavedSearchUseCase,
)
from src.app.stores import wiring as stores_wiring


def _alerts(db: Session) -> SearchAlertsOverAlerts:
    return SearchAlertsOverAlerts(alerts_wiring.price_alerts(db))


def saved_searches(db: Session) -> SavedSearchRepositoryInterface:
    """Saved searches' repository, for searches' own controllers."""
    return SavedSearchRepository(db)


def search_runs(db: Session) -> SearchRunRepositoryInterface:
    """Search runs' repository, for searches' own controllers."""
    return SearchRunRepository(db)


def saved_search_validator(db: Session) -> SavedSearchValidator:
    """Checks create and update requests against saved searches and stores."""
    return SavedSearchValidator(
        SavedSearchRepository(db),
        SearchStoresOverStores(stores_wiring.store_by_id(db)),
    )


def search_run_validator(db: Session) -> SearchRunValidator:
    """Checks run create requests (status, counts, the search exists)."""
    return SearchRunValidator(SearchRunRepository(db), SavedSearchRepository(db))


def create_saved_search(db: Session) -> CreateSavedSearchUseCase:
    return CreateSavedSearchUseCase(SavedSearchRepository(db))


def saved_search_by_id(db: Session) -> GetSavedSearchUseCase:
    return GetSavedSearchUseCase(SavedSearchRepository(db))


def saved_search_by_term(db: Session) -> FindSavedSearchByTermUseCase:
    return FindSavedSearchByTermUseCase(SavedSearchRepository(db))


def update_saved_search(db: Session) -> UpdateSavedSearchUseCase:
    return UpdateSavedSearchUseCase(SavedSearchRepository(db))


def delete_saved_search(db: Session) -> DeleteSavedSearchUseCase:
    return DeleteSavedSearchUseCase(SavedSearchRepository(db), _alerts(db))


def run_search_now(db: Session) -> RunSearchNowUseCase:
    return RunSearchNowUseCase(
        SearchRunRepository(db),
        _alerts(db),
        RunLimitsOverBilling(billing_wiring.user_plan_limits(db)),
        CelerySearchDispatcher(),
    )


def list_search_runs(db: Session) -> ListSearchRunsUseCase:
    """Pages of search runs (the admin summary shows the latest ones)."""
    return ListSearchRunsUseCase(SearchRunRepository(db))
