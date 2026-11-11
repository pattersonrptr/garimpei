import logging
import os
import random
from datetime import datetime, timedelta

import redis
import requests

from celery import Celery, chord, group
from src.api.api_client import ApiClient
from src.celery.search_run import SearchRun, title_matches
from src.scrapers.factory.scraper_factory import ScraperFactory
from src.scrapers.manager.scraper_manager import ScraperManager

logger = logging.getLogger(__name__)

broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
app = Celery(main="scrapers", broker=broker_url, backend="redis://redis:6379/0")

_redis = redis.Redis.from_url(broker_url, decode_responses=True)


def get_celery_worker_token():
    api_base_url = os.getenv("API_URL", "http://web:8000")
    auth_url = f"{api_base_url}/auth/login"
    payload = {
        "username": os.getenv("CELERY_WORKER_USERNAME"),
        "password": os.getenv("CELERY_WORKER_PASSWORD"),
        "grant_type": "password",
        "scope": "",
        "client_id": "",
        "client_secret": "",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(auth_url, data=payload, headers=headers)
        response.raise_for_status()
        # Response is JSON:API: {"data": {"attributes": {"access_token": "..."}}}
        body = response.json()
        token = (
            body.get("data", {}).get("attributes", {}).get("access_token")
            or body.get("access_token")  # fallback for plain JSON
        )
        return token
    except requests.exceptions.RequestException as e:
        logger.error("Error when trying to retrieve Celery worker token: %s", e)
        return None


@app.task(name="src.celery.tasks.run_scraper_search")
def run_scraper_search(search_config_id: int):
    """Dispatch parallel search tasks for each active source website in a search config.

    Uses a Redis lock to prevent the same search config from running
    concurrently.  The lock auto-expires after 30 minutes as a safety net.
    """
    lock_key = f"search_config_lock:{search_config_id}"

    # Try to acquire lock (SET NX with 30-minute TTL)
    if not _redis.set(lock_key, "running", nx=True, ex=1800):
        logger.info(
            "Search config %s is already running (lock held), skipping.",
            search_config_id,
        )
        return {
            "status": "skipped",
            "message": f"Search config {search_config_id} is already running",
        }

    try:
        return _run_scraper_search_locked(search_config_id)
    except Exception:
        # Release lock on unexpected failure so the config can be re-triggered
        _redis.delete(lock_key)
        raise


def _run_scraper_search_locked(search_config_id: int):
    """Inner implementation, called while the Redis lock is held.

    Opens one execution log for the whole run and one step per site; see
    src/celery/search_run.py for how the run is closed.
    """
    client = ApiClient(get_celery_worker_token())
    search_config = client.get_search_config_by_id(search_config_id)

    if not search_config:
        _release_lock(search_config_id)
        logger.error("Search config %s not found, skipping.", search_config_id)
        return {
            "status": "error",
            "message": f"Search config {search_config_id} not found",
        }

    searches = []
    for source_website_id in search_config.get("source_website_ids", []):
        # Each id in source_website_ids is an int; we need the name for the scraper factory
        # We fetch the source website to check is_active and retrieve name
        response = requests.get(
            f"{client.base_url}/source-websites/{source_website_id}",
            headers=client.headers,
            timeout=10,
        )
        if response.status_code == 200:
            sw = ApiClient._extract_attributes(response.json())
            if sw.get("is_active"):
                searches.append(
                    {
                        "search_config_id": search_config_id,
                        "search_term": search_config["search_term"],
                        "scraper_name": sw["name"],
                    }
                )

    if not searches:
        client.create_search_execution_log(
            search_config_id=search_config_id,
            status="failed",
            error_message="None of the search's websites is active",
        )
        _release_lock(search_config_id)
        logger.warning(
            "No active source websites for search config %s", search_config_id
        )
        return {"status": "skipped", "message": "No active source websites"}

    log = client.create_search_execution_log(
        search_config_id=search_config_id, status="running"
    )
    log_id = log.get("id")
    if log_id:
        SearchRun(_redis, log_id).start(steps=len(searches))
    else:
        logger.warning("Could not open a run log for config %s", search_config_id)

    return group(
        run_search.s(s["search_term"], s["scraper_name"], s["search_config_id"], log_id)
        for s in searches
    )()


@app.task(name="src.celery.tasks.run_search")
def run_search(
    search: str,
    scraper_name: str,
    search_config_id: int,
    log_id: str | None = None,
):
    """Collect the listing URLs for a term on one site and queue their scraping.

    Every listing found is scraped again, new or not: that is how known
    listings get their current price.
    """
    client = ApiClient(get_celery_worker_token())
    run = SearchRun(_redis, log_id) if log_id else None

    try:
        scraper = ScraperManager(ScraperFactory().create_scraper(scraper_name))
        urls = list(dict.fromkeys(scraper.get_products_urls(search)))
        chunks = list(scraper.split_search_urls({"search": search, "urls": urls}, 20))
        if run:
            run.add_steps(len(chunks))
            run.add("listings_found", len(urls))
            _report_progress(client, run)
        for chunk in chunks:
            scrape_batch.apply_async(
                args=[chunk, scraper_name, search_config_id, log_id, search],
                countdown=5,
            )
        result = {"status": "success", "search": search, "urls_count": len(urls)}
    except Exception as e:
        logger.error(
            "Error in run_search for '%s' on '%s': %s", search, scraper_name, e
        )
        if run:
            run.add_error(f"{scraper_name}: {e}")
        result = {"status": "error", "search": search, "message": str(e)}

    _step_done(client, run, search_config_id)
    return result


@app.task(name="src.celery.tasks.scrape_batch")
def scrape_batch(
    urls: list[str],
    scraper_name: str,
    search_config_id: int | None = None,
    log_id: str | None = None,
    search_term: str | None = None,
):
    """Scrape a batch of URLs using a single browser, then save results.

    This avoids the memory cost of launching a separate Chromium process
    for every single URL (the old ``scrape_product_page`` approach).

    Rate-limiting is handled by each scraper internally (e.g.
    ``MercadoLivreScraper`` applies its own delays between requests).
    """
    scraper_instance = ScraperFactory().create_scraper(scraper_name)
    scraper = ScraperManager(scraper_instance)
    results = []

    # Shuffle URLs if the scraper requests it (anti-sequential pattern
    # to avoid behavioural detection — e.g. MercadoLivreScraper).
    if getattr(scraper_instance, "_SHUFFLE_URLS", False):
        urls = list(urls)  # copy so we don't mutate the original
        random.shuffle(urls)
        logger.info("🔀 URLs shuffled for %s (%d URLs)", scraper_name, len(urls))

    try:
        for url in urls:
            try:
                product_data = scraper.scrape_product(url)
                results.append({"status": "success", "data": product_data})
            except Exception as e:
                logger.warning("Failed to scrape %s: %s", url, e)
                results.append({"status": "error", "url": url, "message": str(e)})
    finally:
        # Ensure browser is closed and loop is torn down after the batch
        if hasattr(scraper_instance, "stop_sync"):
            scraper_instance.stop_sync()

    # Persist immediately (no chord needed)
    return save_products(results, scraper_name, search_config_id, log_id, search_term)


@app.task(name="src.celery.tasks.scrape_product_page")
def scrape_product_page(url: str, scraper_name: str):
    """Scrape a single product page and return the extracted data.

    Kept for backward-compatibility / one-off scrapes.  For bulk work
    prefer ``scrape_batch`` which reuses the browser across URLs.
    """
    scraper = ScraperManager(ScraperFactory().create_scraper(scraper_name))
    try:
        product_data = scraper.scrape_product(url)
        return {"status": "success", "data": product_data}
    except Exception as e:
        return {"status": "error", "url": url, "message": str(e)}


@app.task(name="src.celery.tasks.save_products")
def save_products(
    results: list,
    scraper_name: str,
    search_config_id: int | None = None,
    log_id: str | None = None,
    search_term: str | None = None,
):
    """Persist scraped listings and their prices, then count the batch in its run.

    With a ``search_term``, only listings whose title contains it are saved:
    marketplaces also return loosely related items, and an alert would never
    match those anyway.
    """
    client = ApiClient(get_celery_worker_token())
    run = SearchRun(_redis, log_id) if log_id else None
    try:
        outcome = _save_results(client, results, scraper_name, search_term)
    except Exception as e:
        logger.error("Saving %s results failed: %s", scraper_name, e)
        if run:
            run.add_error(f"{scraper_name}: {e}")
        outcome = {"status": "error", "message": str(e), "processed": 0}

    if run:
        run.add("listings_checked", len(results))
        run.add("results_count", outcome.get("processed", 0))
        _report_progress(client, run)
    _step_done(client, run, search_config_id)
    return outcome


def _save_results(
    client: ApiClient, results: list, scraper_name: str, search_term: str | None
) -> dict:
    if not results:
        return {"status": "error", "message": "No products to save", "processed": 0}

    source_website = client.get_source_website_by_name(scraper_name.lower())
    website_id = source_website.get("id")

    successful = [
        {**r["data"], "source_website_id": website_id}
        for r in results
        if r.get("status") == "success"
    ]
    if not successful:
        return {
            "status": "error",
            "message": "All scraping attempts failed",
            "processed": 0,
        }

    matching = (
        [p for p in successful if title_matches(p.get("title", ""), search_term)]
        if search_term
        else successful
    )
    unrelated = len(successful) - len(matching)
    if unrelated:
        logger.info(
            "Skipped %d listing(s) whose title does not contain '%s'",
            unrelated,
            search_term,
        )

    created = 0
    for product_data in matching:
        url = product_data.get("url")
        if not url:
            continue
        existing = client.get_product_by_url(url)
        raw_price = product_data.get("price") or product_data.get("current_price")
        current_price = float(raw_price) if raw_price else None
        if existing:
            product_id = existing.get("id")
            if product_id and current_price is not None:
                client.create_price_history(product_id, current_price)
            client.update_product(product_id, product_data)
        else:
            created_product = client.create_product(product_data)
            product_id = created_product.get("id") if created_product else None
            if product_id and current_price is not None:
                client.create_price_history(product_id, current_price)
            if created_product:
                created += 1
        if product_id and current_price is not None:
            try:
                client.evaluate_product_alerts(product_id)
            except Exception as e:
                logger.warning(
                    "Alert evaluation failed for product %s: %s", product_id, e
                )

    return {
        "status": "success",
        "created": created,
        "processed": len(matching),
        "unrelated": unrelated,
    }


@app.task(name="src.celery.tasks.run_scraper_update")
def run_scraper_update(scraper_name: str):
    """Re-scrape all products updated more than 30 days ago for a given scraper."""
    cutoff_date = (datetime.today() - timedelta(days=30)).date()
    products = ApiClient(get_celery_worker_token()).get_products(
        {"updated_before": str(cutoff_date), "source_website_name": scraper_name}
    )

    if not products:
        return {"status": "skipped", "message": "No products to update"}

    return chord(
        update_product.s(product, scraper_name).set(countdown=10)
        for product in products
    )(update_products.s(scraper_name))


@app.task(name="src.celery.tasks.update_product")
def update_product(product: dict, scraper_name: str):
    """Re-scrape a single product and return fresh data."""
    scraper = ScraperManager(ScraperFactory().create_scraper(scraper_name))
    try:
        product_data = scraper.update_product(product)
        return {"status": "success", "data": product_data}
    except Exception as e:
        return {"status": "error", "url": product.get("url"), "message": str(e)}


@app.task(name="src.celery.tasks.update_products")
def update_products(results: list, scraper_name: str):
    """Persist updated product data and record price history entries."""
    client = ApiClient(get_celery_worker_token())

    if not results:
        return {"status": "error", "message": "No products to update"}

    source_website = client.get_source_website_by_name(scraper_name.lower())
    website_id = source_website.get("id")

    successful = [
        {**r["data"], "source_website_id": website_id}
        for r in results
        if r.get("status") == "success"
    ]

    if not successful:
        return {"status": "error", "message": "All update attempts failed"}

    updated = 0
    for product_data in successful:
        product_id = product_data.get("id")
        if not product_id:
            continue
        result = client.update_product(product_id, product_data)
        if result:
            raw_price = product_data.get("price") or product_data.get("current_price")
            current_price = float(raw_price) if raw_price else None
            if current_price is not None:
                client.create_price_history(product_id, current_price)
            updated += 1

    return {"status": "success", "updated": updated}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _release_lock(search_config_id: int | None) -> None:
    if search_config_id is not None:
        _redis.delete(f"search_config_lock:{search_config_id}")


def _report_progress(client: ApiClient, run: SearchRun) -> None:
    """Send the run's counters to its execution log (the UI polls them)."""
    client.update_search_execution_log(run.log_id, **run.snapshot())


def _step_done(
    client: ApiClient, run: SearchRun | None, search_config_id: int | None
) -> None:
    """Count one finished step; the last one closes the run and frees the lock."""
    if run is None or not run.step_done():
        return
    counters = run.snapshot()
    errors = run.errors()
    # Failed only when nothing worked; partial errors are reported on success.
    failed = bool(errors) and counters["listings_found"] == 0
    client.update_search_execution_log(
        run.log_id,
        status="failed" if failed else "success",
        error_message="; ".join(errors)[:1000] or None,
        **counters,
    )
    run.clear()
    _release_lock(search_config_id)


app.conf.timezone = "America/Sao_Paulo"
app.conf.beat_scheduler = "src.celery.beat_schedule.DynamicScheduler"


@app.task(name="src.celery.tasks.cleanup_orphaned_products")
def cleanup_orphaned_products(days_old: int = 30):
    """Daily task: remove products older than `days_old` days with no matching alert."""
    token = get_celery_worker_token()
    if not token:
        logger.error("Cannot run cleanup: failed to get auth token")
        return {"status": "error", "message": "Auth token unavailable"}

    api_base_url = os.getenv("API_URL", "http://web:8000")
    url = f"{api_base_url}/admin/cleanup-products?days_old={days_old}&dry_run=false"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.post(url, headers=headers, timeout=120)
        response.raise_for_status()
        result = response.json()
        attrs = result.get("data", {}).get("attributes", {})
        logger.info(
            "Cleanup completed: %d products deleted",
            attrs.get("deleted-count", 0),
        )
        return {"status": "success", **attrs}
    except requests.exceptions.RequestException as e:
        logger.error("Cleanup task failed: %s", e)
        return {"status": "error", "message": str(e)}


# ---------------------------------------------------------------------------
# Daily offer collection (comparator, Phase 2e)
# ---------------------------------------------------------------------------

COLLECT_DAILY_LOCK = "collectors:daily_lock"
# Longer than a full run (about an hour for 50 books and 3 stores at 5-15 s a
# request), so two hourly ticks never collect at once; it still expires if
# the worker dies mid-run.
COLLECT_DAILY_LOCK_SECONDS = 4 * 60 * 60


@app.task(name="src.celery.tasks.collect_daily_offers")
def collect_daily_offers():
    """Beat calls this every hour. Each store is collected once a day (the
    first tick after the PC is on), stalest books first; see CollectDaily."""
    from src.collectors.wiring import collect_daily

    if not _redis.set(
        COLLECT_DAILY_LOCK, "running", nx=True, ex=COLLECT_DAILY_LOCK_SECONDS
    ):
        logger.info("Daily collection already running, skipping this tick.")
        return {"status": "skipped", "message": "already running"}
    try:
        outcomes = collect_daily(_redis)
    finally:
        _redis.delete(COLLECT_DAILY_LOCK)

    summary = {}
    for outcome in outcomes:
        report = outcome.report
        line = outcome.status
        if report:
            line += (
                f": {report.sent} offers sent, {len(report.not_found)} not found, "
                f"{len(report.failed)} failed"
            )
        if outcome.detail:
            line += f" ({outcome.detail})"
        if outcome.status in ("collected", "already_done", "paused"):
            logger.info("Collection %s: %s", outcome.store_name, line)
        else:
            logger.warning("Collection %s: %s", outcome.store_name, line)
        summary[outcome.store_name] = line
    return {"status": "success", "stores": summary}


# ---------------------------------------------------------------------------
# Notification tasks
# ---------------------------------------------------------------------------


@app.task(name="src.celery.tasks.send_price_alert_notifications")
def send_price_alert_notifications(search_config_id: int | None = None):
    """Check active price alerts and send email notifications for matching products.

    If search_config_id is provided, only check alerts linked to that config.
    Otherwise, check all active alerts.

    Called automatically after save_products or can be triggered manually.
    """
    client = ApiClient(get_celery_worker_token())
    alerts = client.get_active_price_alerts()

    if search_config_id is not None:
        alerts = [a for a in alerts if a.get("search_config_id") == search_config_id]

    if not alerts:
        logger.info("No active price alerts to notify for config=%s", search_config_id)
        return {"status": "skipped", "message": "No active alerts"}

    results = []
    for alert in alerts:
        alert_id = alert.get("id")
        if not alert_id:
            continue
        try:
            result = client.trigger_price_alert_notification(alert_id)
            results.append({"alert_id": alert_id, "result": result})
        except Exception as e:
            logger.error("Notification failed for alert %s: %s", alert_id, e)
            results.append({"alert_id": alert_id, "error": str(e)})

    sent = sum(
        1
        for r in results
        if r.get("result", {}).get("data", {}).get("attributes", {}).get("status")
        == "sent"
    )
    return {
        "status": "success",
        "alerts_checked": len(alerts),
        "notifications_sent": sent,
    }
