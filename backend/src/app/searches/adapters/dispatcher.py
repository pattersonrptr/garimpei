"""SearchDispatcher over the Celery client (the scrapers' queue)."""

from src.app.infrastructure.celery_client import dispatch_scraper_search
from src.app.searches.ports import SearchDispatcher


class CelerySearchDispatcher(SearchDispatcher):
    def dispatch(self, search_id: int) -> str:
        return dispatch_scraper_search(search_id)
