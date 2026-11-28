"""Admin responses as the admin page and the scrapers read them
(JSON:API-like, kebab-case)."""

from datetime import datetime

from src.app.admin.entities import AdminSummary, RecentRun
from src.app.catalog.entities import StaleProductsCleanup


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _run(run: RecentRun) -> dict:
    return {
        "id": run.id,
        "search-config-id": run.search_id,
        "status": run.status,
        "results-count": run.results_count,
        "error-message": run.error_message,
        "started-at": _iso(run.started_at),
        "finished-at": _iso(run.finished_at),
    }


def present_summary(summary: AdminSummary) -> dict:
    return {
        "data": {
            "type": "admin-summary",
            "id": "1",
            "attributes": {
                "total-users": summary.users.total,
                "active-users": summary.users.active,
                "total-products": summary.products,
                "total-alerts": summary.alerts.total,
                "active-alerts": summary.alerts.active,
                "total-source-websites": summary.stores.total,
                "active-source-websites": summary.stores.active,
                "recent-executions": [_run(r) for r in summary.recent_runs],
                "scraper-stats": {
                    "recent-total": summary.scraper_stats.recent_total,
                    "success-count": summary.scraper_stats.success_count,
                    "failed-count": summary.scraper_stats.failed_count,
                },
            },
        }
    }


def present_cleanup(result: StaleProductsCleanup, *, dry_run: bool) -> dict:
    return {
        "data": {
            "type": "cleanup-result",
            "id": "1",
            "attributes": {
                "dry-run": dry_run,
                "eligible-count": result.eligible,
                "deleted-count": result.deleted,
            },
        }
    }
