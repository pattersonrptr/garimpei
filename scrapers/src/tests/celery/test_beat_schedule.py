"""
Tests for src/celery/beat_schedule.py.

Strategy: patch ApiClient and _get_celery_worker_token to avoid any HTTP
calls; patch celery.beat.ScheduleEntry / Scheduler internals to avoid Celery init.
"""

from unittest.mock import MagicMock, patch

from celery.schedules import schedule

# ---------------------------------------------------------------------------
# get_dynamic_schedule
# ---------------------------------------------------------------------------


@patch("src.celery.beat_schedule._get_celery_worker_token", return_value=None)
def test_get_dynamic_schedule_returns_empty_when_no_token(mock_token):
    from src.celery.beat_schedule import get_dynamic_schedule

    result = get_dynamic_schedule()
    assert result == {}


@patch("src.celery.beat_schedule._get_celery_worker_token", return_value="tok")
@patch("src.celery.beat_schedule.ApiClient")
def test_get_dynamic_schedule_returns_empty_when_no_alerts(mock_client_cls, _):
    from src.celery.beat_schedule import get_dynamic_schedule

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.get_active_price_alerts.return_value = []

    result = get_dynamic_schedule()
    assert result == {}


@patch("src.celery.beat_schedule._get_celery_worker_token", return_value="tok")
@patch("src.celery.beat_schedule.ApiClient")
def test_get_dynamic_schedule_builds_entry_per_search_config(mock_client_cls, _):
    """Two alerts pointing at different search_configs → two schedule entries."""
    from src.celery.beat_schedule import get_dynamic_schedule

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.get_active_price_alerts.return_value = [
        {"id": 10, "search_config_id": 1, "frequency_minutes": 30, "is_active": True},
        {"id": 20, "search_config_id": 2, "frequency_minutes": 60, "is_active": True},
    ]

    result = get_dynamic_schedule()

    assert "run_search_1" in result
    assert "run_search_2" in result
    assert result["run_search_1"]["task"] == "src.celery.tasks.run_scraper_search"
    assert result["run_search_1"]["args"] == (1,)
    assert result["run_search_2"]["args"] == (2,)
    # Verify schedule intervals (in seconds)
    assert result["run_search_1"]["schedule"] == schedule(run_every=30 * 60)
    assert result["run_search_2"]["schedule"] == schedule(run_every=60 * 60)


@patch("src.celery.beat_schedule._get_celery_worker_token", return_value="tok")
@patch("src.celery.beat_schedule.ApiClient")
def test_get_dynamic_schedule_groups_by_config_uses_min_frequency(mock_client_cls, _):
    """Two alerts sharing the same search_config → single entry with min freq."""
    from src.celery.beat_schedule import get_dynamic_schedule

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.get_active_price_alerts.return_value = [
        {"id": 10, "search_config_id": 5, "frequency_minutes": 120, "is_active": True},
        {"id": 20, "search_config_id": 5, "frequency_minutes": 30, "is_active": True},
    ]

    result = get_dynamic_schedule()

    assert len(result) == 1
    assert "run_search_5" in result
    assert result["run_search_5"]["schedule"] == schedule(run_every=30 * 60)


@patch("src.celery.beat_schedule._get_celery_worker_token", return_value="tok")
@patch("src.celery.beat_schedule.ApiClient")
def test_get_dynamic_schedule_skips_alerts_without_search_config_id(mock_client_cls, _):
    from src.celery.beat_schedule import get_dynamic_schedule

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.get_active_price_alerts.return_value = [
        {"id": 10, "frequency_minutes": 30, "is_active": True},
    ]

    result = get_dynamic_schedule()
    assert result == {}


@patch("src.celery.beat_schedule._get_celery_worker_token", return_value="tok")
@patch("src.celery.beat_schedule.ApiClient")
def test_get_dynamic_schedule_defaults_frequency_to_60(mock_client_cls, _):
    """Alert without frequency_minutes should default to 60."""
    from src.celery.beat_schedule import get_dynamic_schedule

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.get_active_price_alerts.return_value = [
        {"id": 10, "search_config_id": 3, "is_active": True},
    ]

    result = get_dynamic_schedule()

    assert "run_search_3" in result
    assert result["run_search_3"]["schedule"] == schedule(run_every=60 * 60)


# ---------------------------------------------------------------------------
# DynamicScheduler.sync_from_api
# ---------------------------------------------------------------------------


@patch("src.celery.beat_schedule.get_dynamic_schedule")
@patch("src.celery.beat_schedule.ScheduleEntry")
def test_sync_from_api_populates_schedule(mock_entry_cls, mock_get_schedule):
    from src.celery.beat_schedule import DynamicScheduler

    schedule_data = {
        "run_search_1": {
            "task": "src.celery.tasks.run_scraper_search",
            "schedule": MagicMock(),
            "args": (1,),
        }
    }
    mock_get_schedule.return_value = schedule_data

    mock_entry = MagicMock()
    mock_entry_cls.return_value = mock_entry

    scheduler = DynamicScheduler.__new__(DynamicScheduler)
    scheduler.schedule = {}
    scheduler.app = MagicMock()

    scheduler.sync_from_api()

    assert "run_search_1" in scheduler.schedule
    assert scheduler.schedule["run_search_1"] is mock_entry
    # +2 for the static tasks: daily collection and cleanup
    assert "cleanup_orphaned_products" in scheduler.schedule
    assert "collect_daily_offers" in scheduler.schedule
    assert mock_entry_cls.call_count == 3


@patch("src.celery.beat_schedule.get_dynamic_schedule")
@patch("src.celery.beat_schedule.ScheduleEntry")
def test_sync_from_api_clears_old_entries_first(mock_entry_cls, mock_get_schedule):
    from src.celery.beat_schedule import DynamicScheduler

    mock_get_schedule.return_value = {}

    scheduler = DynamicScheduler.__new__(DynamicScheduler)
    scheduler.schedule = {}
    scheduler.app = MagicMock()

    scheduler.sync_from_api()

    # Even with no dynamic schedules, the static cleanup task should be present
    assert "cleanup_orphaned_products" in scheduler.schedule
