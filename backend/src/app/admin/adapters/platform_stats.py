"""Admin's PlatformStats over the use cases of accounts, alerts, catalog,
stores and searches."""

from src.app.accounts.use_cases import CountUsersUseCase
from src.app.admin.entities import Counts, RecentRun
from src.app.admin.ports import PlatformStats
from src.app.alerts.use_cases import CountPriceAlertsUseCase
from src.app.catalog.use_cases import CountProductsUseCase
from src.app.searches.use_cases import ListSearchRunsUseCase
from src.app.stores.use_cases import CountStoresUseCase


class PlatformStatsOverModules(PlatformStats):
    def __init__(
        self,
        *,
        users: CountUsersUseCase,
        alerts: CountPriceAlertsUseCase,
        products: CountProductsUseCase,
        stores: CountStoresUseCase,
        runs: ListSearchRunsUseCase,
    ):
        self._users = users
        self._alerts = alerts
        self._products = products
        self._stores = stores
        self._runs = runs

    def users(self) -> Counts:
        return Counts(
            total=self._users.execute(),
            active=self._users.execute(active_only=True),
        )

    def alerts(self) -> Counts:
        return Counts(
            total=self._alerts.execute(),
            active=self._alerts.execute(active_only=True),
        )

    def products(self) -> int:
        return self._products.execute()

    def stores(self) -> Counts:
        return Counts(
            total=self._stores.execute(),
            active=self._stores.execute(active_only=True),
        )

    def recent_runs(self, limit: int) -> list[RecentRun]:
        runs, _ = self._runs.execute(
            limit=limit, sort_by="started_at", sort_order="desc"
        )
        return [
            RecentRun(
                id=run.id,
                search_id=run.search_config_id,
                status=run.status,
                results_count=run.results_count,
                error_message=run.error_message,
                started_at=run.started_at,
                finished_at=run.finished_at,
            )
            for run in runs
            if run.id is not None
        ]
