from src.app.admin.entities import AdminSummary, ScraperStats
from src.app.admin.ports import PlatformStats

RECENT_RUNS = 20


class GetAdminSummaryUseCase:
    def __init__(self, stats: PlatformStats):
        self.stats = stats

    def execute(self) -> AdminSummary:
        """The platform's counts and its latest runs."""
        runs = self.stats.recent_runs(RECENT_RUNS)
        return AdminSummary(
            users=self.stats.users(),
            alerts=self.stats.alerts(),
            products=self.stats.products(),
            stores=self.stats.stores(),
            recent_runs=runs,
            scraper_stats=ScraperStats.of(runs),
        )
