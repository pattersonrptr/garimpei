import logging
import time

from celery.beat import ScheduleEntry, Scheduler
from celery.schedules import crontab, schedule
from src.api.api_client import ApiClient

logger = logging.getLogger(__name__)


def _get_celery_worker_token():
    """Re-use the same auth helper used by Celery tasks."""
    import os

    import requests

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
        body = response.json()
        token = body.get("data", {}).get("attributes", {}).get(
            "access_token"
        ) or body.get("access_token")
        return token
    except requests.exceptions.RequestException as e:
        logger.error("Error retrieving Celery worker token for beat: %s", e)
        return None


def get_dynamic_schedule():
    """Build a Celery Beat schedule from active price alerts.

    Groups alerts by ``search_config_id`` and uses the **minimum**
    ``frequency_minutes`` across all alerts that share the same config.
    The Redis lock inside ``run_scraper_search`` guarantees that the
    same config won't run concurrently — so the beat schedule is just
    the desired interval; the task itself is safe to call repeatedly.
    """
    token = _get_celery_worker_token()
    if not token:
        logger.error("Could not authenticate for beat schedule — skipping sync.")
        return {}

    client = ApiClient(token)
    alerts = client.get_active_price_alerts()

    if not alerts:
        logger.info("No active price alerts — nothing to schedule.")
        return {}

    # Group by search_config_id → min frequency_minutes
    config_frequency: dict[int, int] = {}
    for alert in alerts:
        sc_id = alert.get("search_config_id")
        freq = alert.get("frequency_minutes", 60)
        if sc_id is None:
            continue
        sc_id = int(sc_id)
        if sc_id not in config_frequency or freq < config_frequency[sc_id]:
            config_frequency[sc_id] = freq

    schedules = {}
    for search_config_id, freq_minutes in config_frequency.items():
        schedules[f"run_search_{search_config_id}"] = {
            "task": "src.celery.tasks.run_scraper_search",
            "schedule": schedule(run_every=freq_minutes * 60),  # seconds
            "args": (search_config_id,),
        }

    logger.info(
        "Beat schedule built: %d search config(s) from %d alert(s)",
        len(schedules),
        len(alerts),
    )
    return schedules


class DynamicScheduler(Scheduler):
    """Celery Beat scheduler that dynamically fetches schedules from the API."""

    def setup_schedule(self):
        while True:
            time.sleep(10)
            self.tick()
            self.sync_from_api()

    def sync_from_api(self):
        logger.info("DynamicScheduler: syncing schedule from API...")

        self.schedule.clear()

        for name, entry in get_dynamic_schedule().items():
            self.schedule[name] = ScheduleEntry(
                name=name,
                task=entry["task"],
                schedule=entry["schedule"],
                args=entry.get("args", ()),
                kwargs=entry.get("kwargs", {}),
                options=entry.get("options", {}),
                app=self.app,
            )

        # Static task: daily offer collection. Every hour, so a PC that was
        # off catches up when it comes back; each store still runs once a day.
        self.schedule["collect_daily_offers"] = ScheduleEntry(
            name="collect_daily_offers",
            task="src.celery.tasks.collect_daily_offers",
            schedule=crontab(minute=5),
            args=(),
            kwargs={},
            options={},
            app=self.app,
        )

        # Static task: cleanup orphaned products daily at 04:00
        self.schedule["cleanup_orphaned_products"] = ScheduleEntry(
            name="cleanup_orphaned_products",
            task="src.celery.tasks.cleanup_orphaned_products",
            schedule=crontab(hour=4, minute=0),
            args=(30,),
            kwargs={},
            options={},
            app=self.app,
        )
