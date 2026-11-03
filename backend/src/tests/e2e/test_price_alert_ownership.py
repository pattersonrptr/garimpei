"""
E2E tests for per-user ownership of price alerts and search configs.

Regular users can create and manage their own alerts (the core feature of the
freemium plan) but must never see or change another user's; staff keep full
access. Other users' resources answer 404 so IDs can't be probed.
"""

import pytest
from passlib.context import CryptContext

from src.app.infrastructure.database.models.user_model import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    response = client.post(
        "/auth/login", data={"username": "otheruser", "password": "Other@1234"}
    )
    assert response.status_code == 200
    token = response.json()["data"]["attributes"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _alert_body(search_term, user_id, source_website_id, max_price=100):
    return {
        "data": {
            "type": "price_alert",
            "attributes": {
                "search_term": search_term,
                "max_price": max_price,
                "user_id": user_id,
                "frequency_minutes": 1440,
                "source_website_ids": [source_website_id],
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
            "clean architecture", sample_user.id, sample_source_website.id
        ),
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


class TestRegularUserOwnAlerts:
    def test_regular_user_can_create_alert(self, user_alert, sample_user):
        assert user_alert["attributes"]["user_id"] == sample_user.id
        assert user_alert["attributes"]["search_config_id"] is not None

    def test_create_ignores_user_id_of_someone_else(
        self, client, auth_headers, sample_user, other_user, sample_source_website
    ):
        response = client.post(
            "/price-alerts/",
            json=_alert_body("python", other_user.id, sample_source_website.id),
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
        assert (
            client.get(f"{base}/opportunities", headers=auth_headers).status_code == 200
        )
        update = client.put(
            base, json=_max_price_update(alert_id, 50), headers=auth_headers
        )
        assert update.status_code == 200
        assert update.json()["data"]["attributes"]["max_price"] == 50
        assert client.delete(base, headers=auth_headers).status_code == 204

    def test_can_check_own_search_status(self, client, auth_headers, user_alert):
        sc_id = user_alert["attributes"]["search_config_id"]
        response = client.get(
            f"/search-configs/{sc_id}/execution-status", headers=auth_headers
        )
        assert response.status_code == 200


class TestIsolationBetweenUsers:
    def test_list_returns_only_own_alerts(
        self, client, auth_headers, other_headers, user_alert
    ):
        mine = client.get("/price-alerts/", headers=auth_headers).json()["data"]
        theirs = client.get("/price-alerts/", headers=other_headers).json()["data"]
        assert [a["id"] for a in mine] == [user_alert["id"]]
        assert theirs == []

    @pytest.mark.parametrize(
        "method,suffix",
        [("get", ""), ("get", "/products"), ("get", "/opportunities"), ("delete", "")],
    )
    def test_other_users_alert_is_not_found(
        self, client, other_headers, user_alert, method, suffix
    ):
        response = getattr(client, method)(
            f"/price-alerts/{user_alert['id']}{suffix}", headers=other_headers
        )
        assert response.status_code == 404

    def test_cannot_update_other_users_alert(self, client, other_headers, user_alert):
        response = client.put(
            f"/price-alerts/{user_alert['id']}",
            json=_max_price_update(user_alert["id"], 1),
            headers=other_headers,
        )
        assert response.status_code == 404

    def test_cannot_list_other_users_alerts_by_user_id(
        self, client, other_headers, sample_user, user_alert
    ):
        response = client.get(
            f"/price-alerts/user/{sample_user.id}", headers=other_headers
        )
        assert response.status_code == 403

    def test_other_users_search_config_is_hidden(
        self, client, other_headers, user_alert
    ):
        sc_id = user_alert["attributes"]["search_config_id"]
        assert (
            client.get(f"/search-configs/{sc_id}", headers=other_headers).status_code
            == 404
        )
        trigger = client.post(f"/search-configs/{sc_id}/trigger", headers=other_headers)
        assert trigger.status_code == 404
        listed = client.get("/search-configs/", headers=other_headers).json()["data"]
        assert listed == []


class TestStaffAndPublicData:
    def test_staff_lists_all_alerts_on_request(
        self, client, staff_auth_headers, user_alert
    ):
        own = client.get("/price-alerts/", headers=staff_auth_headers).json()["data"]
        everyone = client.get(
            "/price-alerts/", params={"all_users": "true"}, headers=staff_auth_headers
        ).json()["data"]
        assert own == []
        assert user_alert["id"] in [a["id"] for a in everyone]

    def test_staff_can_read_any_alert_and_config(
        self, client, staff_auth_headers, user_alert
    ):
        response = client.get(
            f"/price-alerts/{user_alert['id']}", headers=staff_auth_headers
        )
        assert response.status_code == 200
        listed = client.get("/search-configs/", headers=staff_auth_headers).json()[
            "data"
        ]
        sc_id = user_alert["attributes"]["search_config_id"]
        assert sc_id in [int(c["id"]) for c in listed]

    def test_regular_user_can_read_public_listings(
        self, client, auth_headers, sample_product
    ):
        assert client.get("/products/", headers=auth_headers).status_code == 200
        assert client.get("/source-websites/", headers=auth_headers).status_code == 200
        assert client.get("/dashboard/summary", headers=auth_headers).status_code == 200

    def test_regular_user_cannot_write_products(
        self, client, auth_headers, sample_product
    ):
        response = client.delete(f"/products/{sample_product.id}", headers=auth_headers)
        assert response.status_code == 403
