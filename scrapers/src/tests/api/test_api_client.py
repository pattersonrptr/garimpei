from unittest.mock import MagicMock, patch

import pytest
import requests

from src.api.api_client import ApiClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return ApiClient(access_token="test_token")


@pytest.fixture
def client_no_token():
    return ApiClient()


def _mock_response(status_code: int, json_data=None):
    """Helper: build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    return resp


def _jsonapi_single(type_name: str, id_: str, **attrs):
    """Helper: wrap attributes in a JSON:API single-resource response."""
    return {"data": {"type": type_name, "id": id_, "attributes": attrs}}


def _jsonapi_collection(type_name: str, items: list[dict]):
    """Helper: wrap a list of dicts in a JSON:API collection response."""
    return {
        "data": [
            {"type": type_name, "id": str(i), "attributes": item}
            for i, item in enumerate(items, start=1)
        ]
    }


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_sets_auth_header(client):
    assert client.headers["Authorization"] == "Bearer test_token"


def test_init_without_token_has_no_auth_header(client_no_token):
    assert "Authorization" not in client_no_token.headers


# ---------------------------------------------------------------------------
# _make_request
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_make_request_success(mock_req, client):
    mock_req.return_value = _mock_response(200, {"ok": True})
    resp = client._make_request("GET", "/test/")
    assert resp.status_code == 200


@patch("requests.request")
def test_make_request_exception_returns_empty_response(mock_req, client):
    mock_req.side_effect = Exception("network error")
    resp = client._make_request("GET", "/test/")
    assert isinstance(resp, requests.Response)


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------


def test_extract_attributes_returns_flat_dict():
    payload = _jsonapi_single("products", "5", title="Notebook", price=999.0)
    result = ApiClient._extract_attributes(payload)
    assert result["id"] == "5"
    assert result["title"] == "Notebook"
    assert result["price"] == 999.0


def test_extract_attributes_missing_data_returns_empty():
    assert ApiClient._extract_attributes({}) == {}
    assert ApiClient._extract_attributes({"data": None}) == {}


def test_extract_collection_returns_list_of_flat_dicts():
    payload = _jsonapi_collection("products", [{"title": "A"}, {"title": "B"}])
    result = ApiClient._extract_collection(payload)
    assert len(result) == 2
    assert result[0]["title"] == "A"
    assert result[1]["id"] == "2"


def test_extract_collection_missing_data_returns_empty():
    assert ApiClient._extract_collection({}) == []


def test_wrap_for_creation():
    result = ApiClient._wrap_for_creation("product", {"url": "http://x.com"})
    assert result == {
        "data": {"type": "product", "attributes": {"url": "http://x.com"}}
    }


def test_wrap_for_update():
    result = ApiClient._wrap_for_update("product", 42, {"title": "New"})
    assert result["data"]["id"] == "42"
    assert result["data"]["type"] == "product"
    assert result["data"]["attributes"]["title"] == "New"


# ---------------------------------------------------------------------------
# Search configs
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_get_search_config_by_id_found(mock_req, client):
    mock_req.return_value = _mock_response(
        200, _jsonapi_single("search_configs", "1", search_term="notebook")
    )
    result = client.get_search_config_by_id(1)
    assert result["id"] == "1"
    assert result["search_term"] == "notebook"


@patch("requests.request")
def test_get_search_config_by_id_not_found(mock_req, client):
    mock_req.return_value = _mock_response(404)
    result = client.get_search_config_by_id(999)
    assert result == {}


@patch("requests.request")
def test_get_active_search_configs_success(mock_req, client):
    mock_req.return_value = _mock_response(
        200,
        _jsonapi_collection(
            "search_configs", [{"search_term": "a"}, {"search_term": "b"}]
        ),
    )
    result = client.get_active_search_configs()
    assert len(result) == 2


@patch("requests.request")
def test_get_active_search_configs_failure(mock_req, client):
    mock_req.return_value = _mock_response(500)
    result = client.get_active_search_configs()
    assert result == []


# ---------------------------------------------------------------------------
# Source websites
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_get_source_website_by_name_found(mock_req, client):
    mock_req.return_value = _mock_response(
        200, _jsonapi_single("source_websites", "2", name="enjoei", is_active=True)
    )
    result = client.get_source_website_by_name("enjoei")
    assert result["name"] == "enjoei"
    assert result["is_active"] is True


@patch("requests.request")
def test_get_source_website_by_name_not_found(mock_req, client):
    mock_req.return_value = _mock_response(404)
    result = client.get_source_website_by_name("unknown")
    assert result == {}


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_get_products_success(mock_req, client):
    mock_req.return_value = _mock_response(
        200,
        _jsonapi_collection(
            "products", [{"url": "http://a.com"}, {"url": "http://b.com"}]
        ),
    )
    result = client.get_products()
    assert len(result) == 2


@patch("requests.request")
def test_get_products_with_params(mock_req, client):
    mock_req.return_value = _mock_response(
        200, _jsonapi_collection("products", [{"url": "http://a.com"}])
    )
    result = client.get_products(params={"source_website_id": "2"})
    assert len(result) == 1
    _, kwargs = mock_req.call_args
    assert kwargs["params"] == {"source_website_id": "2"}


@patch("requests.request")
def test_get_products_failure_returns_empty(mock_req, client):
    mock_req.return_value = _mock_response(500)
    assert client.get_products() == []


@patch("requests.request")
def test_get_product_by_url_found(mock_req, client):
    mock_req.return_value = _mock_response(
        200, _jsonapi_single("products", "7", url="http://x.com", title="X")
    )
    result = client.get_product_by_url("http://x.com")
    assert result["title"] == "X"


@patch("requests.request")
def test_get_product_by_url_not_found(mock_req, client):
    mock_req.return_value = _mock_response(404)
    assert client.get_product_by_url("http://missing.com") == {}


@patch("requests.request")
def test_get_product_by_url_not_found_is_not_an_error(mock_req, client, caplog):
    # A listing seen for the first time is the normal case, not an error
    response = _mock_response(404)
    response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    mock_req.return_value = response
    with caplog.at_level("ERROR"):
        client.get_product_by_url("http://missing.com")
    assert caplog.records == []


def test_product_exists_true(client):
    with patch.object(client, "get_product_by_url", return_value={"id": "1"}):
        assert client.product_exists("http://a.com") is True


def test_product_exists_false(client):
    with patch.object(client, "get_product_by_url", return_value={}):
        assert client.product_exists("http://a.com") is False


@patch("requests.request")
def test_create_product_success(mock_req, client):
    mock_req.return_value = _mock_response(
        201, _jsonapi_single("products", "10", url="http://new.com")
    )
    result = client.create_product({"url": "http://new.com", "title": "New"})
    assert result["id"] == "10"
    # Verify correct JSON:API type is sent
    _, kwargs = mock_req.call_args
    assert kwargs["json"]["data"]["type"] == "product"


@patch("requests.request")
def test_create_product_failure_returns_empty(mock_req, client):
    mock_req.return_value = _mock_response(400)
    result = client.create_product({"url": "http://bad.com"})
    assert result == {}


@patch("requests.request")
def test_update_product_success(mock_req, client):
    mock_req.return_value = _mock_response(
        200, _jsonapi_single("products", "3", title="Updated")
    )
    result = client.update_product(3, {"title": "Updated"})
    assert result["title"] == "Updated"
    _, kwargs = mock_req.call_args
    assert kwargs["json"]["data"]["type"] == "product"


@patch("requests.request")
def test_update_product_failure_returns_empty(mock_req, client):
    mock_req.return_value = _mock_response(404)
    assert client.update_product(99, {"title": "X"}) == {}


def test_create_new_products_skips_existing(client):
    with (
        patch.object(client, "product_exists", side_effect=[True, False, False]),
        patch.object(client, "create_product", return_value={"id": "1"}),
    ):
        count = client.create_new_products([{"url": "a"}, {"url": "b"}, {"url": "c"}])
    assert count == 2


def test_create_new_products_all_existing(client):
    with patch.object(client, "product_exists", return_value=True):
        assert client.create_new_products([{"url": "a"}, {"url": "b"}]) == 0


def test_update_product_list_success(client):
    with patch.object(client, "update_product", return_value={"id": "1"}):
        count = client.update_product_list([{"id": "1"}, {"id": "2"}])
    assert count == 2


def test_update_product_list_partial_failure(client):
    with patch.object(client, "update_product", side_effect=[{"id": "1"}, {}]):
        count = client.update_product_list([{"id": "1"}, {"id": "2"}])
    assert count == 1


def test_get_existing_product_urls(client):
    with (
        patch.object(client, "get_source_website_by_name", return_value={"id": "2"}),
        patch.object(
            client,
            "get_products",
            return_value=[
                {"url": "http://a.com"},
                {"url": "http://b.com"},
                {"url": None},
            ],
        ),
    ):
        urls = client.get_existing_product_urls("enjoei")
    assert urls == {"http://a.com", "http://b.com"}


def test_get_existing_product_urls_no_website(client):
    with patch.object(client, "get_source_website_by_name", return_value={}):
        assert client.get_existing_product_urls("unknown") == set()


# ---------------------------------------------------------------------------
# Price histories
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_create_price_history_success(mock_req, client):
    mock_req.return_value = _mock_response(
        201, _jsonapi_single("price_histories", "1", product_id=5, price=99.9)
    )
    result = client.create_price_history(5, 99.9)
    assert result["price"] == 99.9
    _, kwargs = mock_req.call_args
    assert kwargs["json"]["data"]["type"] == "price_history"


@patch("requests.request")
def test_create_price_history_failure_returns_empty(mock_req, client):
    mock_req.return_value = _mock_response(422)
    assert client.create_price_history(5, 99.9) == {}


# ---------------------------------------------------------------------------
# Search execution logs
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_create_search_execution_log_success(mock_req, client):
    mock_req.return_value = _mock_response(
        201,
        _jsonapi_single(
            "search_execution_logs", "1", search_config_id=2, status="running"
        ),
    )
    result = client.create_search_execution_log(search_config_id=2, status="running")
    assert result["status"] == "running"
    _, kwargs = mock_req.call_args
    assert kwargs["json"]["data"]["type"] == "search_execution_log"


@patch("requests.request")
def test_create_search_execution_log_with_error_message(mock_req, client):
    mock_req.return_value = _mock_response(
        201,
        _jsonapi_single(
            "search_execution_logs", "2", search_config_id=1, status="failed"
        ),
    )
    result = client.create_search_execution_log(
        search_config_id=1, status="failed", error_message="timeout"
    )
    assert result["status"] == "failed"
    _, kwargs = mock_req.call_args
    assert kwargs["json"]["data"]["attributes"]["error_message"] == "timeout"


@patch("requests.request")
def test_create_search_execution_log_failure_returns_empty(mock_req, client):
    mock_req.return_value = _mock_response(400)
    assert (
        client.create_search_execution_log(search_config_id=1, status="running") == {}
    )


# ---------------------------------------------------------------------------
# evaluate_product_alerts
# ---------------------------------------------------------------------------


@patch("requests.request")
def test_evaluate_product_alerts_success(mock_req, client):
    mock_req.return_value = _mock_response(
        200,
        {
            "data": {
                "type": "evaluate_alerts_results",
                "attributes": {
                    "status": "sent",
                    "message": "1 notification(s) sent, 0 skipped (dedup)",
                    "notifications_sent": 1,
                    "skipped": 0,
                },
            }
        },
    )
    result = client.evaluate_product_alerts(42)
    assert result["data"]["attributes"]["notifications_sent"] == 1
    # Verify a POST was made to the correct endpoint
    call_args = mock_req.call_args
    method_arg = call_args[0][0] if call_args[0] else call_args[1].get("method")
    assert method_arg == "POST"
    url_arg = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("url")
    assert "/products/42/evaluate-alerts" in url_arg


@patch("requests.request")
def test_evaluate_product_alerts_failure_returns_empty(mock_req, client):
    mock_req.return_value = _mock_response(500)
    result = client.evaluate_product_alerts(42)
    assert result == {}


@patch("requests.request")
def test_evaluate_product_alerts_not_found(mock_req, client):
    mock_req.return_value = _mock_response(404)
    result = client.evaluate_product_alerts(9999)
    assert result == {}
