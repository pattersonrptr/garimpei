"""Composition root for the collectors: the store adapters, the backend API
and the run log. Both entry points use it: the command line (run.py) and the
daily Celery task."""

import os
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

from src.collectors.api_sink import ApiCollectionQueue, ApiOfferSink, login
from src.collectors.polite_http import PoliteHttpClient
from src.collectors.ports import OfferSource
from src.collectors.redis_run_log import RedisStoreRunLog
from src.collectors.stores.estante_virtual import EstanteVirtualSource
from src.collectors.stores.vtex import VtexSource
from src.collectors.use_cases import CollectDaily, StoreOutcome

# Each store gets its own polite client (its own pauses and robots.txt).
STORES: dict[str, Callable[[], OfferSource]] = {
    "estante-virtual": lambda: EstanteVirtualSource(PoliteHttpClient()),
    "livraria-da-vila": lambda: VtexSource(
        PoliteHttpClient(),
        store_name="livraria_da_vila",
        base_url="https://www.livrariadavila.com.br",
    ),
    "martins-fontes": lambda: VtexSource(
        PoliteHttpClient(),
        store_name="martins_fontes",
        base_url="https://www.martinsfontespaulista.com.br",
    ),
}

# The stores' "day" is Brazil's (no daylight saving since 2019), not the
# container's UTC.
BRAZIL = timezone(timedelta(hours=-3))


def backend() -> tuple[str, Callable[[], str]]:
    """The backend's URL and a login for the collectors' service account,
    from the same variables the scraper worker uses."""
    base_url = os.getenv("API_URL", "http://localhost:8000")
    username = os.environ["CELERY_WORKER_USERNAME"]
    password = os.environ["CELERY_WORKER_PASSWORD"]
    return base_url, lambda: login(base_url, username, password)


def offer_sink() -> ApiOfferSink:
    return ApiOfferSink(*backend())


def collect_daily(redis, today: date | None = None) -> list[StoreOutcome]:
    """Run the daily collection over every store, one after the other, so only
    one request is ever in flight."""
    base_url, authenticate = backend()
    return CollectDaily(
        sources=[make() for make in STORES.values()],
        queue=ApiCollectionQueue(base_url, authenticate),
        sink=ApiOfferSink(base_url, authenticate),
        run_log=RedisStoreRunLog(redis),
        today=today or datetime.now(BRAZIL).date(),
    ).execute()
