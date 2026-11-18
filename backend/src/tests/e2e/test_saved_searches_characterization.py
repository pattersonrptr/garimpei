"""Characterization tests before the saved searches module (search configs).

They pin today's behavior over HTTP, so the refactor that moves search
configs and their runs into their own module can prove it changed nothing.
Each test kills a mutation that survived the existing suite (Nov 18, 2026).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.searches.persistence.models import SavedSearch as SavedSearchModel
from src.app.searches.persistence.models import SearchRun as SearchRunModel
from src.app.stores.persistence.models import Store as StoreModel

DISPATCH = "src.app.searches.adapters.dispatcher.dispatch_scraper_search"


def add_config(test_db, user, search_term="dom casmurro", stores=(), **fields):
    config = SavedSearchModel(
        search_term=search_term,
        is_active=fields.pop("is_active", True),
        frequency_days=fields.pop("frequency_days", 1),
        user_id=user.id,
        **fields,
    )
    config.source_websites.extend(stores)
    test_db.add(config)
    test_db.commit()
    test_db.refresh(config)
    return config


def add_store(test_db, name):
    store = StoreModel(name=name, base_url=f"https://{name}.example.com")
    test_db.add(store)
    test_db.commit()
    test_db.refresh(store)
    return store


def add_alert(test_db, user, config):
    alert = PriceAlertModel(
        search_term=config.search_term,
        max_price=30.0,
        is_active=True,
        user_id=user.id,
        search_config_id=config.id,
    )
    test_db.add(alert)
    test_db.commit()
    return alert


def add_run(test_db, config, started_minutes_ago, **fields):
    log = SearchRunModel(
        search_config_id=config.id,
        status=fields.pop("status", "success"),
        started_at=datetime.now(UTC) - timedelta(minutes=started_minutes_ago),
        **fields,
    )
    test_db.add(log)
    test_db.commit()
    test_db.refresh(log)
    return log


class TestListSearchConfigs:
    def test_newest_config_comes_first(
        self, client, staff_auth_headers, test_db, sample_user
    ):
        add_config(test_db, sample_user, "first")
        add_config(test_db, sample_user, "second")

        response = client.get("/search-configs/", headers=staff_auth_headers)

        terms = [item["attributes"]["search_term"] for item in response.json()["data"]]
        assert terms == ["second", "first"]

    def test_regular_user_cannot_list_another_users_configs(
        self, client, auth_headers, sample_staff_user
    ):
        response = client.get(
            f"/search-configs/user/{sample_staff_user.id}", headers=auth_headers
        )

        assert response.status_code == 403


class TestPartialUpdate:
    """A PUT that sends one attribute keeps every other one as it was."""

    def test_fields_left_out_keep_their_values(
        self, client, staff_auth_headers, test_db, sample_user, sample_store
    ):
        config = add_config(
            test_db,
            sample_user,
            "dom casmurro",
            stores=[sample_store],
            is_active=False,
            frequency_days=7,
            search_metadata={"isbn": "9788535910663"},
        )

        response = client.put(
            f"/search-configs/{config.id}",
            json={
                "data": {
                    "type": "search_config",
                    "attributes": {"preferred_time": "08:30:00"},
                }
            },
            headers=staff_auth_headers,
        )

        assert response.status_code == 200, response.text
        attributes = response.json()["data"]["attributes"]
        assert attributes["search_term"] == "dom casmurro"
        assert attributes["is_active"] is False
        assert attributes["frequency_days"] == 7
        assert attributes["search_metadata"] == {"isbn": "9788535910663"}
        assert attributes["source_website_ids"] == [sample_store.id]


class TestRunNow:
    def test_own_config_without_an_alert_is_not_found(
        self, client, auth_headers, sample_search_config
    ):
        with patch(DISPATCH) as dispatch:
            response = client.post(
                f"/search-configs/{sample_search_config.id}/trigger",
                headers=auth_headers,
            )

        assert response.status_code == 404
        dispatch.assert_not_called()

    def test_more_stores_than_the_plan_allows_is_refused(
        self, client, auth_headers, test_db, sample_user
    ):
        stores = [add_store(test_db, f"store{n}") for n in range(3)]  # free plan: 2
        config = add_config(test_db, sample_user, stores=stores)
        add_alert(test_db, sample_user, config)

        with patch(DISPATCH) as dispatch:
            response = client.post(
                f"/search-configs/{config.id}/trigger", headers=auth_headers
            )

        assert response.status_code == 403
        error = response.json()["errors"][0]
        assert error["code"] == "PLAN_LIMIT_REACHED"
        assert error["meta"]["limit"] == "max_sources"
        dispatch.assert_not_called()


class TestExecutionStatus:
    def test_never_run_config_is_idle(self, client, auth_headers, sample_search_config):
        response = client.get(
            f"/search-configs/{sample_search_config.id}/execution-status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["data"]["attributes"]["status"] == "idle"

    def test_failed_run_shows_its_error_message(
        self, client, auth_headers, test_db, sample_search_config
    ):
        add_run(
            test_db,
            sample_search_config,
            started_minutes_ago=5,
            status="failed",
            error_message="Store answered 503",
        )

        response = client.get(
            f"/search-configs/{sample_search_config.id}/execution-status",
            headers=auth_headers,
        )

        attributes = response.json()["data"]["attributes"]
        assert attributes["status"] == "failed"
        assert attributes["error_message"] == "Store answered 503"


class TestRunsOfAConfig:
    def test_latest_run_comes_first(
        self, client, staff_auth_headers, test_db, sample_search_config
    ):
        older = add_run(test_db, sample_search_config, started_minutes_ago=120)
        newer = add_run(test_db, sample_search_config, started_minutes_ago=10)

        response = client.get(
            f"/search-execution-logs/search-config/{sample_search_config.id}",
            headers=staff_auth_headers,
        )

        ids = [int(item["id"]) for item in response.json()["data"]]
        assert ids == [newer.id, older.id]
