"""
E2E tests for per-user access to price alerts and search configs.

- Regular users manage their own alerts (the core feature of the free plan)
  and can "Run Now" only the searches behind their own active alerts, within
  their plan limits. Other users' resources answer 404 so IDs can't be probed.
- Staff (incl. the Celery service user) and superusers keep full access:
  the scrapers and Celery Beat list every active alert and search config.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from passlib.context import CryptContext

from src.app.infrastructure.database.models.search_execution_log_model import (
    SearchExecutionLog as SearchExecutionLogModel,
)
from src.app.infrastructure.database.models.user_model import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DISPATCH = (
    "src.app.interfaces.http.controllers.search_config_controller"
    ".dispatch_scraper_search"
)


def _login(client, username, password):
    response = client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200
    token = response.json()["data"]["attributes"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user(test_db):
    user = User(
        username="otheruser",
        email="other@example.com",
        hashed_password=pwd_context.hash("Other@1234"),
        is_superuser=False,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def other_headers(client, other_user):
    return _login(client, "otheruser", "Other@1234")


@pytest.fixture
def service_headers(client, test_db):
    """Same role as the Celery worker account: staff, not superuser."""
    user = User(
        username="celery_user",
        email="celery_user@example.com",
        hashed_password=pwd_context.hash("Celery@1234"),
        is_superuser=False,
        is_staff=True,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    return _login(client, "celery_user", "Celery@1234")


def _alert_body(search_term, user_id, source_website_ids, max_price=100):
    return {
        "data": {
            "type": "price_alert",
            "attributes": {
                "search_term": search_term,
                "max_price": max_price,
                "user_id": user_id,
                "frequency_minutes": 1440,
                "source_website_ids": source_website_ids,
            },
        }
    }


def _max_price_update(alert_id, max_price):
    return {
        "data": {
            "type": "price_alert",
            "id": alert_id,
            "attributes": {"max_price": max_price},
        }
    }


@pytest.fixture
def user_alert(client, auth_headers, sample_user, sample_source_website):
    response = client.post(
        "/price-alerts/",
        json=_alert_body(
            "clean architecture", sample_user.id, [sample_source_website.id]
        ),
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _add_run(test_db, search_config_id, minutes_ago, status="success"):
    log = SearchExecutionLogModel(
        search_config_id=search_config_id,
        status=status,
        started_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )
    test_db.add(log)
    test_db.commit()


# ============================================================================
# Regular user: own alerts
# ============================================================================


class TestRegularUserOwnAlerts:
    def test_can_create_alert(self, user_alert, sample_user):
        assert user_alert["attributes"]["user_id"] == sample_user.id
        assert user_alert["attributes"]["search_config_id"] is not None

    def test_create_ignores_user_id_of_someone_else(
        self, client, auth_headers, sample_user, other_user, sample_source_website
    ):
        response = client.post(
            "/price-alerts/",
            json=_alert_body("python", other_user.id, [sample_source_website.id]),
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["data"]["attributes"]["user_id"] == sample_user.id

    def test_can_read_update_and_delete_own_alert(
        self, client, auth_headers, user_alert
    ):
        alert_id = user_alert["id"]
        base = f"/price-alerts/{alert_id}"
        assert client.get(base, headers=auth_headers).status_code == 200
        assert client.get(f"{base}/products", headers=auth_headers).status_code == 200
        assert (
            client.get(f"{base}/opportunities", headers=auth_headers).status_code == 200
        )
        update = client.put(
            base, json=_max_price_update(alert_id, 50), headers=auth_headers
        )
        assert update.status_code == 200
        assert update.json()["data"]["attributes"]["max_price"] == 50
        assert client.delete(base, headers=auth_headers).status_code == 204

    def test_list_returns_only_own_alerts(
        self, client, auth_headers, other_headers, user_alert
    ):
        mine = client.get("/price-alerts/", headers=auth_headers).json()["data"]
        theirs = client.get("/price-alerts/", headers=other_headers).json()["data"]
        assert [a["id"] for a in mine] == [user_alert["id"]]
        assert theirs == []

    def test_can_check_own_search_status(self, client, auth_headers, user_alert):
        sc_id = user_alert["attributes"]["search_config_id"]
        response = client.get(
            f"/search-configs/{sc_id}/execution-status", headers=auth_headers
        )
        assert response.status_code == 200

    def test_cannot_manage_search_configs_directly(
        self, client, auth_headers, sample_user, sample_source_website, user_alert
    ):
        """Search configs come from alerts; creating one directly would bypass the plan."""
        body = {
            "data": {
                "type": "search_config",
                "attributes": {
                    "search_term": "anything",
                    "user_id": sample_user.id,
                    "source_website_ids": [sample_source_website.id],
                },
            }
        }
        assert (
            client.post("/search-configs/", json=body, headers=auth_headers).status_code
            == 403
        )
        sc_id = user_alert["attributes"]["search_config_id"]
        assert (
            client.delete(f"/search-configs/{sc_id}", headers=auth_headers).status_code
            == 403
        )


# ============================================================================
# Regular user: "Run Now"
# ============================================================================


class TestRunNow:
    def test_can_trigger_search_of_own_active_alert(
        self, client, auth_headers, user_alert
    ):
        sc_id = user_alert["attributes"]["search_config_id"]
        with patch(DISPATCH, return_value="task-1") as dispatch:
            response = client.post(
                f"/search-configs/{sc_id}/trigger", headers=auth_headers
            )
        assert response.status_code == 202, response.text
        dispatch.assert_called_once_with(sc_id)

    def test_blocked_within_plan_interval(
        self, client, auth_headers, user_alert, test_db
    ):
        sc_id = user_alert["attributes"]["search_config_id"]
        _add_run(test_db, sc_id, minutes_ago=30)  # free plan: 360 min
        with patch(DISPATCH) as dispatch:
            response = client.post(
                f"/search-configs/{sc_id}/trigger", headers=auth_headers
            )
        assert response.status_code == 403
        assert response.json()["errors"][0]["code"] == "PLAN_LIMIT_REACHED"
        dispatch.assert_not_called()

    def test_allowed_after_plan_interval(
        self, client, auth_headers, user_alert, test_db
    ):
        sc_id = user_alert["attributes"]["search_config_id"]
        _add_run(test_db, sc_id, minutes_ago=400)
        with patch(DISPATCH, return_value="task-2"):
            response = client.post(
                f"/search-configs/{sc_id}/trigger", headers=auth_headers
            )
        assert response.status_code == 202

    def test_running_search_still_answers_409(
        self, client, auth_headers, user_alert, test_db
    ):
        sc_id = user_alert["attributes"]["search_config_id"]
        _add_run(test_db, sc_id, minutes_ago=1, status="running")
        with patch(DISPATCH) as dispatch:
            response = client.post(
                f"/search-configs/{sc_id}/trigger", headers=auth_headers
            )
        assert response.status_code == 409
        dispatch.assert_not_called()

    def test_can_trigger_search_of_paused_alert(self, client, auth_headers, user_alert):
        # Pausing stops the schedule and the emails, not a manual check.
        alert_id = user_alert["id"]
        deactivate = {
            "data": {
                "type": "price_alert",
                "id": alert_id,
                "attributes": {"is_active": False},
            }
        }
        assert (
            client.put(
                f"/price-alerts/{alert_id}", json=deactivate, headers=auth_headers
            ).status_code
            == 200
        )
        sc_id = user_alert["attributes"]["search_config_id"]
        with patch(DISPATCH, return_value="task-paused") as dispatch:
            response = client.post(
                f"/search-configs/{sc_id}/trigger", headers=auth_headers
            )
        assert response.status_code == 202
        dispatch.assert_called_once_with(int(sc_id))


# ============================================================================
# Another user's alert
# ============================================================================


class TestOtherUsersAlert:
    @pytest.mark.parametrize(
        "method,suffix",
        [("get", ""), ("get", "/products"), ("get", "/opportunities"), ("delete", "")],
    )
    def test_is_not_found(self, client, other_headers, user_alert, method, suffix):
        response = getattr(client, method)(
            f"/price-alerts/{user_alert['id']}{suffix}", headers=other_headers
        )
        assert response.status_code == 404

    def test_cannot_update(self, client, other_headers, user_alert):
        response = client.put(
            f"/price-alerts/{user_alert['id']}",
            json=_max_price_update(user_alert["id"], 1),
            headers=other_headers,
        )
        assert response.status_code == 404

    def test_cannot_list_by_user_id(
        self, client, other_headers, sample_user, user_alert
    ):
        response = client.get(
            f"/price-alerts/user/{sample_user.id}", headers=other_headers
        )
        assert response.status_code == 403

    def test_search_config_is_hidden_and_cannot_be_triggered(
        self, client, other_headers, user_alert
    ):
        sc_id = user_alert["attributes"]["search_config_id"]
        assert (
            client.get(f"/search-configs/{sc_id}", headers=other_headers).status_code
            == 404
        )
        with patch(DISPATCH) as dispatch:
            trigger = client.post(
                f"/search-configs/{sc_id}/trigger", headers=other_headers
            )
        assert trigger.status_code == 404
        dispatch.assert_not_called()
        listed = client.get("/search-configs/", headers=other_headers).json()["data"]
        assert listed == []


# ============================================================================
# Admin (superuser) and the Celery service user (staff)
# ============================================================================


class TestAdmin:
    def test_my_alerts_lists_only_own_alerts(
        self, client, superuser_auth_headers, user_alert
    ):
        listed = client.get("/price-alerts/", headers=superuser_auth_headers).json()[
            "data"
        ]
        assert user_alert["id"] not in [a["id"] for a in listed]

    def test_lists_and_reads_every_alert(
        self, client, superuser_auth_headers, user_alert
    ):
        listed = client.get(
            "/price-alerts/", params={"scope": "all"}, headers=superuser_auth_headers
        ).json()["data"]
        assert user_alert["id"] in [a["id"] for a in listed]
        response = client.get(
            f"/price-alerts/{user_alert['id']}", headers=superuser_auth_headers
        )
        assert response.status_code == 200

    def test_triggers_any_search_without_plan_interval(
        self, client, superuser_auth_headers, user_alert, test_db
    ):
        sc_id = user_alert["attributes"]["search_config_id"]
        _add_run(test_db, sc_id, minutes_ago=1)
        with patch(DISPATCH, return_value="task-3"):
            response = client.post(
                f"/search-configs/{sc_id}/trigger", headers=superuser_auth_headers
            )
        assert response.status_code == 202


class TestServiceUser:
    """The scrapers authenticate as a staff user (CELERY_WORKER_USERNAME)."""

    def test_lists_every_active_alert(self, client, service_headers, user_alert):
        # scrapers ApiClient.get_active_price_alerts
        listed = client.get(
            "/price-alerts/",
            params={"limit": 100, "scope": "all"},
            headers=service_headers,
        ).json()["data"]
        assert user_alert["id"] in [a["id"] for a in listed]

    def test_lists_every_search_config(self, client, service_headers, user_alert):
        listed = client.get("/search-configs/", headers=service_headers).json()["data"]
        sc_id = user_alert["attributes"]["search_config_id"]
        assert sc_id in [int(c["id"]) for c in listed]

    def test_can_notify_alert(self, client, service_headers, user_alert):
        response = client.post(
            f"/price-alerts/{user_alert['id']}/notify", headers=service_headers
        )
        assert response.status_code != 403


class TestPublicListingData:
    def test_regular_user_can_read(self, client, auth_headers, sample_product):
        assert client.get("/products/", headers=auth_headers).status_code == 200
        assert client.get("/source-websites/", headers=auth_headers).status_code == 200
        assert client.get("/dashboard/summary", headers=auth_headers).status_code == 200

    def test_regular_user_cannot_write_products(
        self, client, auth_headers, sample_product
    ):
        response = client.delete(f"/products/{sample_product.id}", headers=auth_headers)
        assert response.status_code == 403

    def test_regular_user_cannot_notify(self, client, auth_headers, user_alert):
        response = client.post(
            f"/price-alerts/{user_alert['id']}/notify", headers=auth_headers
        )
        assert response.status_code == 403
