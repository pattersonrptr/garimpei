"""
Tests for src/product_scrapers/celery/tasks.py.

Strategy: All external I/O (HTTP via requests, Celery task dispatch,
ScraperFactory/ScraperManager) is mocked so these tests run without any
running infrastructure.
"""

from typing import cast
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.celery.search_run import SearchRun, title_matches
from src.celery.tasks import (
    get_celery_worker_token,
    run_scraper_search,
    run_scraper_update,
    run_search,
    save_products,
    scrape_product_page,
    send_price_alert_notifications,
    update_product,
    update_products,
)


@pytest.fixture(autouse=True)
def _mock_redis():
    """Prevent every test from needing a real Redis connection.

    The module-level ``_redis`` client is used for distributed locks;
    we replace it with a MagicMock so tests never hit the network.
    """
    with patch("src.celery.tasks._redis", new_callable=MagicMock):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeRedis:
    """Just enough of redis-py for SearchRun (hashes, lists, delete)."""

    def __init__(self):
        self.hashes: dict[str, dict[str, int]] = {}
        self.lists: dict[str, list[str]] = {}

    def hset(self, key, mapping):
        self.hashes.setdefault(key, {}).update({k: int(v) for k, v in mapping.items()})

    def expire(self, key, seconds):
        return True

    def hincrby(self, key, field, amount):
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = bucket.get(field, 0) + amount
        return bucket[field]

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)

    def lrange(self, key, start, end):
        return list(self.lists.get(key, []))

    def delete(self, *keys):
        for key in keys:
            self.hashes.pop(key, None)
            self.lists.pop(key, None)


@pytest.fixture
def fake_redis():
    redis_client = FakeRedis()
    with patch("src.celery.tasks._redis", redis_client):
        yield redis_client


def _mock_response(status_code: int, json_data=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    return resp


def _token_response(token: str = "test_jwt_token"):
    """Build the JSON:API login response that the API returns."""
    return {"data": {"attributes": {"access_token": token}}}


def _make_client_mock(token="test_jwt_token"):
    client = MagicMock()
    client.create_search_execution_log.return_value = {"id": "42"}
    client.get_existing_product_urls.return_value = set()
    client.get_source_website_by_name.return_value = {"id": "2"}
    return client


# ---------------------------------------------------------------------------
# get_celery_worker_token
# ---------------------------------------------------------------------------


@patch("requests.post")
def test_get_celery_worker_token_success(mock_post):
    mock_post.return_value = _mock_response(200, _token_response("abc.jwt.token"))
    token = get_celery_worker_token()
    assert token == "abc.jwt.token"


@patch("requests.post")
def test_get_celery_worker_token_parses_jsonapi_path(mock_post):
    """Regression: must read data.attributes.access_token, not root key."""
    payload = {"data": {"attributes": {"access_token": "deep_token"}}}
    mock_post.return_value = _mock_response(200, payload)
    assert get_celery_worker_token() == "deep_token"


@patch("requests.post")
def test_get_celery_worker_token_fallback_to_plain_json(mock_post):
    """Fallback: if JSON:API path is absent, try root-level access_token."""
    mock_post.return_value = _mock_response(200, {"access_token": "plain_token"})
    assert get_celery_worker_token() == "plain_token"


@patch("requests.post")
def test_get_celery_worker_token_returns_none_on_http_error(mock_post):
    mock_post.side_effect = requests.exceptions.RequestException("connection refused")
    assert get_celery_worker_token() is None


@patch("requests.post")
def test_get_celery_worker_token_returns_none_when_token_missing(mock_post):
    mock_post.return_value = _mock_response(200, {"data": {"attributes": {}}})
    # Both paths return falsy → token is None / ""
    result = get_celery_worker_token()
    assert not result


# ---------------------------------------------------------------------------
# run_search
# ---------------------------------------------------------------------------


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
@patch("src.celery.tasks.ScraperFactory")
@patch("src.celery.tasks.ScraperManager")
@patch("src.celery.tasks.scrape_batch")
def test_run_search_queues_every_listing_found_with_the_term(
    mock_batch,
    mock_manager_cls,
    mock_factory_cls,
    mock_client_cls,
    mock_token,
    fake_redis,
):
    client = _make_client_mock()
    mock_client_cls.return_value = client
    mock_manager = MagicMock()
    # duplicates are scraped once; known listings are scraped again (new prices)
    mock_manager.get_products_urls.return_value = ["url1", "url2", "url1", "url3"]
    mock_manager.split_search_urls.return_value = [["url1", "url2"], ["url3"]]
    mock_manager_cls.return_value = mock_manager
    SearchRun(fake_redis, "42").start(steps=1)

    result = run_search("notebook", "enjoei", 1, "42")

    assert result == {"status": "success", "search": "notebook", "urls_count": 3}
    mock_manager.split_search_urls.assert_called_once_with(
        {"search": "notebook", "urls": ["url1", "url2", "url3"]}, 20
    )
    mock_batch.apply_async.assert_any_call(
        args=[["url3"], "enjoei", 1, "42", "notebook"], countdown=5
    )
    run = SearchRun(fake_redis, "42")
    assert run.snapshot()["listings_found"] == 3
    # one site step finished, two batch steps pending
    assert fake_redis.hashes[run.key]["pending"] == 2
    client.update_search_execution_log.assert_called_with(
        "42", listings_found=3, listings_checked=0, results_count=0
    )


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
@patch("src.celery.tasks.ScraperFactory")
@patch("src.celery.tasks.ScraperManager")
def test_run_with_no_listings_is_closed_as_success(
    mock_manager_cls, mock_factory_cls, mock_client_cls, mock_token, fake_redis
):
    """Used to stay "running" forever: no batch was queued to close it."""
    client = _make_client_mock()
    mock_client_cls.return_value = client
    mock_manager = MagicMock()
    mock_manager.get_products_urls.return_value = []
    mock_manager.split_search_urls.return_value = []
    mock_manager_cls.return_value = mock_manager
    SearchRun(fake_redis, "42").start(steps=1)

    run_search("notebook", "enjoei", 7, "42")

    client.update_search_execution_log.assert_called_with(
        "42",
        status="success",
        error_message=None,
        listings_found=0,
        listings_checked=0,
        results_count=0,
    )
    assert fake_redis.hashes == {}  # run cleared


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
@patch("src.celery.tasks.ScraperFactory")
@patch("src.celery.tasks.ScraperManager")
def test_run_search_error_closes_the_run_as_failed(
    mock_manager_cls, mock_factory_cls, mock_client_cls, mock_token, fake_redis
):
    client = _make_client_mock()
    mock_client_cls.return_value = client
    mock_factory_cls.return_value.create_scraper.side_effect = ValueError(
        "not supported"
    )
    SearchRun(fake_redis, "42").start(steps=1)

    result = run_search("x", "bad_scraper", 1, "42")

    assert result["status"] == "error"
    call = client.update_search_execution_log.call_args
    assert call.kwargs["status"] == "failed"
    assert "bad_scraper: not supported" in call.kwargs["error_message"]


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_last_batch_closes_the_run_with_totals(mock_client_cls, mock_token, fake_redis):
    client = _make_client_mock()
    client.get_product_by_url.return_value = {"id": "5"}
    mock_client_cls.return_value = client
    run = SearchRun(fake_redis, "42")
    run.start(steps=1)  # one batch left
    run.add("listings_found", 2)

    save_products(
        [
            _scrape_result("http://a.com", 50.0, "Notebook Dell"),
            _scrape_result("http://b.com", 70.0, "Mouse pad"),
        ],
        "enjoei",
        search_config_id=1,
        log_id="42",
        search_term="notebook",
    )

    client.update_search_execution_log.assert_called_with(
        "42",
        status="success",
        error_message=None,
        listings_found=2,
        listings_checked=2,
        results_count=1,
    )


def test_title_matches_ignores_case_and_accents():
    assert title_matches("Microsserviços Prontos Para Produção", "microsservicos")
    assert title_matches("PYTHON FLUENTE - 2ª edição", "python fluente")
    assert not title_matches("A linguagem de Deus", "python fluente")


# ---------------------------------------------------------------------------
# save_products
# ---------------------------------------------------------------------------


def _scrape_result(url: str, price: float = 99.0, title: str = "Test Product"):
    return {
        "status": "success",
        "data": {
            "url": url,
            "title": title,
            "price": price,
            "current_price": price,
            "source_website_id": "2",
        },
    }


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_save_products_creates_new_products(mock_client_cls, mock_token):
    client = _make_client_mock()
    client.get_product_by_url.return_value = {}  # product does not exist yet
    client.create_product.return_value = {"id": "10"}
    mock_client_cls.return_value = client

    results = [
        _scrape_result("http://a.com", 50.0),
        _scrape_result("http://b.com", 75.0),
    ]
    outcome = save_products(results, "enjoei", search_config_id=1, log_id="42")

    assert outcome["status"] == "success"
    assert outcome["created"] == 2
    assert outcome["processed"] == 2
    assert client.create_product.call_count == 2
    assert client.create_price_history.call_count == 2
    # evaluate_product_alerts called once per new product with price
    assert client.evaluate_product_alerts.call_count == 2


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_save_products_updates_existing_products(mock_client_cls, mock_token):
    client = _make_client_mock()
    client.get_product_by_url.return_value = {"id": "5"}  # product exists
    mock_client_cls.return_value = client

    results = [_scrape_result("http://a.com", 120.0)]
    outcome = save_products(results, "enjoei", search_config_id=1)

    assert outcome["created"] == 0
    client.update_product.assert_called_once()
    client.create_price_history.assert_called_once_with("5", 120.0)
    # evaluate_product_alerts called for the updated product
    client.evaluate_product_alerts.assert_called_once_with("5")


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_save_products_empty_results_returns_error(mock_client_cls, mock_token):
    client = _make_client_mock()
    mock_client_cls.return_value = client

    outcome = save_products([], "enjoei", search_config_id=1)
    assert outcome["status"] == "error"
    assert outcome["message"] == "No products to save"


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_save_products_all_failed_scrapes(mock_client_cls, mock_token):
    client = _make_client_mock()
    mock_client_cls.return_value = client

    results = [
        {"status": "error", "url": "http://a.com", "message": "timeout"},
        {"status": "error", "url": "http://b.com", "message": "timeout"},
    ]
    outcome = save_products(results, "enjoei", search_config_id=1)
    assert outcome["status"] == "error"
    assert outcome["message"] == "All scraping attempts failed"


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_save_products_skips_result_without_url(mock_client_cls, mock_token):
    client = _make_client_mock()
    mock_client_cls.return_value = client

    results = [
        {
            "status": "success",
            "data": {
                "title": "No URL product",
                "current_price": 10.0,
                "source_website_id": "2",
            },
        }
    ]
    outcome = save_products(results, "enjoei", search_config_id=1)
    assert outcome["created"] == 0


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_save_products_no_price_skips_price_history(mock_client_cls, mock_token):
    client = _make_client_mock()
    client.get_product_by_url.return_value = {}
    client.create_product.return_value = {"id": "11"}
    mock_client_cls.return_value = client

    results = [
        {
            "status": "success",
            "data": {"url": "http://a.com", "title": "X", "source_website_id": "2"},
        }
        # No current_price
    ]
    outcome = save_products(results, "enjoei", search_config_id=1)
    assert outcome["created"] == 1
    client.create_price_history.assert_not_called()
    # No price → no evaluate call for new product
    client.evaluate_product_alerts.assert_not_called()


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_save_products_evaluate_alerts_failure_does_not_break(
    mock_client_cls, mock_token
):
    """evaluate_product_alerts failure should be caught and not break save_products."""
    client = _make_client_mock()
    client.get_product_by_url.return_value = {"id": "5"}
    client.evaluate_product_alerts.side_effect = Exception("connection timeout")
    mock_client_cls.return_value = client

    results = [_scrape_result("http://a.com", 120.0)]
    outcome = save_products(results, "enjoei", search_config_id=1)

    # Should succeed despite evaluate failure
    assert outcome["status"] == "success"
    assert outcome["processed"] == 1
    client.evaluate_product_alerts.assert_called_once()


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_save_products_keeps_only_listings_that_match_the_term(
    mock_client_cls, mock_token
):
    client = _make_client_mock()
    client.get_product_by_url.return_value = {}
    client.create_product.return_value = {"id": "10"}
    mock_client_cls.return_value = client

    outcome = save_products(
        [
            _scrape_result("http://a.com", 50.0, "Python Fluente, 2ª edição"),
            _scrape_result("http://b.com", 20.0, "A linguagem de Deus"),
        ],
        "estante_virtual",
        search_term="python fluente",
    )

    assert outcome["processed"] == 1
    assert outcome["unrelated"] == 1
    client.create_product.assert_called_once()


# ---------------------------------------------------------------------------
# send_price_alert_notifications
# ---------------------------------------------------------------------------


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_send_notifications_triggers_for_matching_alerts(mock_client_cls, mock_token):
    client = MagicMock()
    client.get_active_price_alerts.return_value = [
        {"id": "100", "search_config_id": 1},
        {"id": "200", "search_config_id": 2},
    ]
    client.trigger_price_alert_notification.return_value = {
        "data": {"attributes": {"status": "sent"}}
    }
    mock_client_cls.return_value = client

    result = send_price_alert_notifications(search_config_id=1)

    assert result["status"] == "success"
    assert result["alerts_checked"] == 1
    assert result["notifications_sent"] == 1
    client.trigger_price_alert_notification.assert_called_once_with("100")


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_send_notifications_skips_when_no_matching_alerts(mock_client_cls, mock_token):
    client = MagicMock()
    client.get_active_price_alerts.return_value = [
        {"id": "100", "search_config_id": 5},
    ]
    mock_client_cls.return_value = client

    result = send_price_alert_notifications(search_config_id=99)

    assert result["status"] == "skipped"
    client.trigger_price_alert_notification.assert_not_called()


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_send_notifications_handles_api_error_gracefully(mock_client_cls, mock_token):
    client = MagicMock()
    client.get_active_price_alerts.return_value = [
        {"id": "100", "search_config_id": 1},
    ]
    client.trigger_price_alert_notification.side_effect = Exception("API error")
    mock_client_cls.return_value = client

    result = send_price_alert_notifications(search_config_id=1)

    assert result["status"] == "success"
    assert result["alerts_checked"] == 1
    assert result["notifications_sent"] == 0


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_send_notifications_checks_all_alerts_when_no_config(
    mock_client_cls, mock_token
):
    client = MagicMock()
    client.get_active_price_alerts.return_value = [
        {"id": "100", "search_config_id": 1},
        {"id": "200", "search_config_id": 2},
    ]
    client.trigger_price_alert_notification.return_value = {
        "data": {"attributes": {"status": "sent"}}
    }
    mock_client_cls.return_value = client

    result = send_price_alert_notifications(search_config_id=None)

    assert result["status"] == "success"
    assert result["alerts_checked"] == 2
    assert result["notifications_sent"] == 2
    assert client.trigger_price_alert_notification.call_count == 2


# ---------------------------------------------------------------------------
# run_scraper_search
# ---------------------------------------------------------------------------


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_run_scraper_search_config_not_found(mock_client_cls, mock_token):
    client = MagicMock()
    client.get_search_config_by_id.return_value = None
    mock_client_cls.return_value = client

    result = run_scraper_search(999)
    assert result["status"] == "error"
    assert "999" in result["message"]


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.requests")
@patch("src.celery.tasks.group")
@patch("src.celery.tasks.ApiClient")
def test_run_scraper_search_dispatches_active_source_websites(
    mock_client_cls, mock_group, mock_requests, mock_token
):
    client = MagicMock()
    client.get_search_config_by_id.return_value = {
        "search_term": "notebook",
        "source_website_ids": [1, 2],
    }
    client.base_url = "http://web:8000"
    client.headers = {}
    mock_client_cls.return_value = client

    # site 1 is active, site 2 is inactive
    def _sw_response(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "source-websites/1" in url:
            resp.json.return_value = {
                "data": {"attributes": {"name": "enjoei", "is_active": True}}
            }
        else:
            resp.json.return_value = {
                "data": {"attributes": {"name": "olx", "is_active": False}}
            }
        return resp

    mock_requests.get.side_effect = _sw_response

    mock_group_instance = MagicMock()
    mock_group.return_value = mock_group_instance
    mock_group_instance.return_value = {"dispatched": True}

    run_scraper_search(1)

    mock_group.assert_called_once()
    # one log for the whole run, opened before the sites are searched
    client.create_search_execution_log.assert_called_once_with(
        search_config_id=1, status="running"
    )


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.requests")
@patch("src.celery.tasks.ApiClient")
def test_run_scraper_search_no_active_websites_returns_skipped(
    mock_client_cls, mock_requests, mock_token
):
    client = MagicMock()
    client.get_search_config_by_id.return_value = {
        "search_term": "notebook",
        "source_website_ids": [1],
    }
    client.base_url = "http://web:8000"
    client.headers = {}
    mock_client_cls.return_value = client

    # _extract_attributes is a static method — patch it on the class mock
    mock_client_cls._extract_attributes.return_value = {
        "name": "olx",
        "is_active": False,
    }

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": {"attributes": {"name": "olx", "is_active": False}}
    }
    mock_requests.get.return_value = resp

    result = run_scraper_search(1)
    assert result["status"] == "skipped"


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.requests")
@patch("src.celery.tasks.ApiClient")
def test_run_scraper_search_non_200_source_website_skipped(
    mock_client_cls, mock_requests, mock_token
):
    client = MagicMock()
    client.get_search_config_by_id.return_value = {
        "search_term": "cadeira",
        "source_website_ids": [5],
    }
    client.base_url = "http://web:8000"
    client.headers = {}
    mock_client_cls.return_value = client

    resp = MagicMock()
    resp.status_code = 404
    mock_requests.get.return_value = resp

    result = run_scraper_search(1)
    assert result["status"] == "skipped"


# ---------------------------------------------------------------------------
# scrape_product_page
# ---------------------------------------------------------------------------


@patch("src.celery.tasks.ScraperFactory")
@patch("src.celery.tasks.ScraperManager")
def test_scrape_product_page_success(mock_manager_cls, mock_factory_cls):
    mock_scraper = MagicMock()
    mock_factory_cls.return_value.create_scraper.return_value = mock_scraper

    mock_manager = MagicMock()
    mock_manager.scrape_product.return_value = {
        "title": "Cool Book",
        "current_price": 25.0,
    }
    mock_manager_cls.return_value = mock_manager

    result = scrape_product_page("http://enjoei.com.br/produto/1", "enjoei")
    result_dict = cast(dict, result)
    assert result_dict["status"] == "success"
    assert result_dict["data"]["title"] == "Cool Book"


@patch("src.celery.tasks.ScraperFactory")
@patch("src.celery.tasks.ScraperManager")
def test_scrape_product_page_exception_returns_error(
    mock_manager_cls, mock_factory_cls
):
    mock_scraper = MagicMock()
    mock_factory_cls.return_value.create_scraper.return_value = mock_scraper

    mock_manager = MagicMock()
    mock_manager.scrape_product.side_effect = Exception("page not found")
    mock_manager_cls.return_value = mock_manager

    result = scrape_product_page("http://enjoei.com.br/produto/bad", "enjoei")
    assert result["status"] == "error"
    assert result["url"] == "http://enjoei.com.br/produto/bad"
    assert "page not found" in result["message"]


# ---------------------------------------------------------------------------
# run_scraper_update
# ---------------------------------------------------------------------------


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_run_scraper_update_no_products_returns_skipped(mock_client_cls, mock_token):
    client = MagicMock()
    client.get_products.return_value = []
    mock_client_cls.return_value = client

    result = run_scraper_update("enjoei")
    assert result["status"] == "skipped"


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.chord")
@patch("src.celery.tasks.ApiClient")
def test_run_scraper_update_dispatches_chord_for_products(
    mock_client_cls, mock_chord, mock_token
):
    client = MagicMock()
    client.get_products.return_value = [{"id": "1"}, {"id": "2"}]
    mock_client_cls.return_value = client

    mock_chord_instance = MagicMock()
    mock_chord.return_value = mock_chord_instance
    mock_chord_instance.return_value = {"dispatched": True}

    run_scraper_update("enjoei")

    mock_chord.assert_called_once()


# ---------------------------------------------------------------------------
# update_product
# ---------------------------------------------------------------------------


@patch("src.celery.tasks.ScraperFactory")
@patch("src.celery.tasks.ScraperManager")
def test_update_product_success(mock_manager_cls, mock_factory_cls):
    mock_scraper = MagicMock()
    mock_factory_cls.return_value.create_scraper.return_value = mock_scraper

    mock_manager = MagicMock()
    mock_manager.update_product.return_value = {
        "title": "Updated",
        "current_price": 30.0,
    }
    mock_manager_cls.return_value = mock_manager

    result = update_product({"id": "7", "url": "http://a.com"}, "enjoei")
    assert result["status"] == "success"
    assert result["data"]["title"] == "Updated"


@patch("src.celery.tasks.ScraperFactory")
@patch("src.celery.tasks.ScraperManager")
def test_update_product_exception_returns_error(mock_manager_cls, mock_factory_cls):
    mock_scraper = MagicMock()
    mock_factory_cls.return_value.create_scraper.return_value = mock_scraper

    mock_manager = MagicMock()
    mock_manager.update_product.side_effect = Exception("scrape error")
    mock_manager_cls.return_value = mock_manager

    result = update_product({"id": "7", "url": "http://a.com"}, "enjoei")
    assert result["status"] == "error"
    assert result["url"] == "http://a.com"


# ---------------------------------------------------------------------------
# update_products
# ---------------------------------------------------------------------------


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_update_products_empty_results_returns_error(mock_client_cls, mock_token):
    client = MagicMock()
    mock_client_cls.return_value = client

    result = update_products([], "enjoei")
    assert result["status"] == "error"
    assert result["message"] == "No products to update"


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_update_products_all_failed_returns_error(mock_client_cls, mock_token):
    client = MagicMock()
    client.get_source_website_by_name.return_value = {"id": "2"}
    mock_client_cls.return_value = client

    results = [
        {"status": "error", "url": "http://a.com", "message": "fail"},
    ]
    result = update_products(results, "enjoei")
    assert result["status"] == "error"
    assert result["message"] == "All update attempts failed"


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_update_products_updates_and_records_price_history(mock_client_cls, mock_token):
    client = MagicMock()
    client.get_source_website_by_name.return_value = {"id": "2"}
    client.update_product.return_value = {"id": "5"}
    mock_client_cls.return_value = client

    results = [
        {
            "status": "success",
            "data": {
                "id": "5",
                "title": "Item",
                "current_price": 45.0,
                "source_website_id": "2",
            },
        }
    ]
    result = update_products(results, "enjoei")
    assert result["status"] == "success"
    assert result["updated"] == 1
    client.update_product.assert_called_once()
    client.create_price_history.assert_called_once_with("5", 45.0)


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_update_products_skips_entry_without_product_id(mock_client_cls, mock_token):
    client = MagicMock()
    client.get_source_website_by_name.return_value = {"id": "2"}
    mock_client_cls.return_value = client

    results = [
        {
            "status": "success",
            "data": {"title": "No ID", "current_price": 10.0, "source_website_id": "2"},
        }
    ]
    result = update_products(results, "enjoei")
    assert result["updated"] == 0
    client.update_product.assert_not_called()


@patch("src.celery.tasks.get_celery_worker_token", return_value="tok")
@patch("src.celery.tasks.ApiClient")
def test_update_products_no_price_skips_price_history(mock_client_cls, mock_token):
    client = MagicMock()
    client.get_source_website_by_name.return_value = {"id": "2"}
    client.update_product.return_value = {"id": "9"}
    mock_client_cls.return_value = client

    results = [
        {
            "status": "success",
            "data": {"id": "9", "title": "Item", "source_website_id": "2"},
            # No current_price
        }
    ]
    result = update_products(results, "enjoei")
    assert result["updated"] == 1
    client.create_price_history.assert_not_called()


# ---------------------------------------------------------------------------
# collect_daily_offers
# ---------------------------------------------------------------------------


def test_daily_collection_runs_under_a_lock_and_releases_it():
    from datetime import date

    from src.celery.tasks import COLLECT_DAILY_LOCK, collect_daily_offers
    from src.collectors.use_cases import CollectionReport, StoreOutcome

    report = CollectionReport(sent=4, not_found=["x"])
    outcomes = [
        StoreOutcome("estante_virtual", "collected", report),
        StoreOutcome("martins_fontes", "paused", detail=f"until {date(2026, 11, 17)}"),
    ]
    redis = MagicMock()
    redis.set.return_value = True
    with (
        patch("src.celery.tasks._redis", redis),
        patch("src.collectors.wiring.collect_daily", return_value=outcomes) as run,
    ):
        result = collect_daily_offers()

    run.assert_called_once_with(redis)
    assert redis.set.call_args.kwargs["nx"] is True
    redis.delete.assert_called_once_with(COLLECT_DAILY_LOCK)
    assert result["stores"] == {
        "estante_virtual": "collected: 4 offers sent, 1 not found, 0 failed",
        "martins_fontes": "paused (until 2026-11-17)",
    }


def test_daily_collection_skips_while_another_run_holds_the_lock():
    from src.celery.tasks import collect_daily_offers

    redis = MagicMock()
    redis.set.return_value = False
    with (
        patch("src.celery.tasks._redis", redis),
        patch("src.collectors.wiring.collect_daily") as run,
    ):
        result = collect_daily_offers()

    run.assert_not_called()
    redis.delete.assert_not_called()
    assert result["status"] == "skipped"


def test_daily_collection_releases_the_lock_when_it_fails():
    from src.celery.tasks import COLLECT_DAILY_LOCK, collect_daily_offers

    redis = MagicMock()
    redis.set.return_value = True
    with (
        patch("src.celery.tasks._redis", redis),
        patch("src.collectors.wiring.collect_daily", side_effect=KeyError("x")),
        pytest.raises(KeyError),
    ):
        collect_daily_offers()

    redis.delete.assert_called_once_with(COLLECT_DAILY_LOCK)
