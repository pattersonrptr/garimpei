"""Builds admin's use cases from a database session.

The composition point for admin's ports: the other modules are reached
through their own wiring and admin's adapters, never through their
repositories or ORM models.
"""

from sqlalchemy.orm import Session

from src.app.accounts import wiring as accounts_wiring
from src.app.admin.adapters.platform_stats import PlatformStatsOverModules
from src.app.admin.use_cases import GetAdminSummaryUseCase
from src.app.alerts import wiring as alerts_wiring
from src.app.catalog import wiring as catalog_wiring
from src.app.searches import wiring as searches_wiring
from src.app.stores import wiring as stores_wiring


def admin_summary(db: Session) -> GetAdminSummaryUseCase:
    return GetAdminSummaryUseCase(
        PlatformStatsOverModules(
            users=accounts_wiring.count_users(db),
            alerts=alerts_wiring.count_price_alerts(db),
            products=catalog_wiring.count_products(db),
            stores=stores_wiring.count_stores(db),
            runs=searches_wiring.list_search_runs(db),
        )
    )
