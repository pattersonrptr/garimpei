"""
E2E tests for the customer journey fixes found in the exploratory test
(docs/qa/exploratory-report.md). Each class names the finding it covers.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from passlib.context import CryptContext

from src.app.alerts.http.price_alert_controller import (
    get_email_service,
)
from src.app.alerts.persistence.models import (
    NotificationLog as NotificationLogModel,
)
from src.app.catalog.persistence.models import (
    PriceHistory as PriceHistoryModel,
)
from src.app.catalog.persistence.models import (
    Product as ProductModel,
)
from src.app.infrastructure.database.models.search_execution_log_model import (
    SearchExecutionLog as SearchExecutionLogModel,
)
from src.app.infrastructure.database.models.source_website_model import (
    SourceWebsite as SourceWebsiteModel,
)
from src.app.infrastructure.database.models.user_model import User
from src.app.interfaces.services.email_service import EmailResult
from src.main import app

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# Helpers and fixtures
# ============================================================================


@pytest.fixture
def email_service():
    """Record the alert emails instead of sending them."""
    service = MagicMock()
    service.send_price_alert_email.return_value = EmailResult(success=True)
    app.dependency_overrides[get_email_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_email_service, None)


@pytest.fixture
def other_site(test_db):
    site = SourceWebsiteModel(
        name="other_site", base_url="https://other.example.com", is_active=True
    )
    test_db.add(site)
    test_db.commit()
    test_db.refresh(site)
    return site


@pytest.fixture
def service_headers(client, test_db):
    """Same role as the Celery worker account: staff, not superuser."""
    test_db.add(
        User(
            username="celery_user",
            email="celery_user@example.com",
            hashed_password=pwd_context.hash("Celery@1234"),
            is_superuser=False,
            is_staff=True,
            is_active=True,
        )
    )
    test_db.commit()
    response = client.post(
        "/auth/login", data={"username": "celery_user", "password": "Celery@1234"}
    )
    token = response.json()["data"]["attributes"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def other_customer(client, test_db):
    """A second regular user and their auth headers."""
    user = User(
        username="othercustomer",
        email="othercustomer@example.com",
        hashed_password=pwd_context.hash("Other@1234"),
        is_superuser=False,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    response = client.post(
        "/auth/login", data={"username": "othercustomer", "password": "Other@1234"}
    )
    token = response.json()["data"]["attributes"]["access_token"]
    return user, {"Authorization": f"Bearer {token}"}


def add_listing(test_db, site, title, price):
    product = ProductModel(
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        title=title,
        is_available=True,
        source_website_id=site.id,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)
    test_db.add(PriceHistoryModel(product_id=product.id, price=price))
    test_db.commit()
    return product


def alert_body(term, user_id, site_ids, max_price=50, frequency=360):
    return {
        "data": {
            "type": "price_alert",
            "attributes": {
                "search_term": term,
                "max_price": max_price,
                "user_id": user_id,
                "frequency_minutes": frequency,
                "source_website_ids": site_ids,
            },
        }
    }


def update_body(alert_id, **attributes):
    return {"data": {"type": "price_alert", "id": alert_id, "attributes": attributes}}


def create_alert(client, headers, user, site, term, max_price=50):
    response = client.post(
        "/price-alerts/",
        json=alert_body(term, user.id, [site.id], max_price),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def titles(response):
    assert response.status_code == 200, response.text
    return {item["attributes"]["title"] for item in response.json()["data"]}


# ============================================================================
# E / F: the products list
# ============================================================================


class TestProductsList:
    def test_customer_sees_only_what_their_alerts_found(
        self,
        client,
        auth_headers,
        sample_user,
        sample_source_website,
        other_site,
        test_db,
        email_service,
    ):
        add_listing(test_db, sample_source_website, "Python Fluente 2a edição", 120)
        add_listing(test_db, other_site, "Python Fluente from another site", 10)
        add_listing(test_db, sample_source_website, "Cookbook nobody asked for", 10)
        create_alert(
            client, auth_headers, sample_user, sample_source_website, "python fluente"
        )

        listed = titles(client.get("/products/", headers=auth_headers))

        assert listed == {"Python Fluente 2a edição"}

    def test_customer_does_not_see_what_other_customers_alerts_found(
        self,
        client,
        auth_headers,
        sample_user,
        sample_source_website,
        test_db,
        email_service,
    ):
        add_listing(test_db, sample_source_website, "Python Fluente", 120)
        add_listing(test_db, sample_source_website, "Clean Code", 120)
        create_alert(
            client, auth_headers, sample_user, sample_source_website, "python fluente"
        )
        other, other_headers = other_customer(client, test_db)
        create_alert(client, other_headers, other, sample_source_website, "clean code")

        assert titles(client.get("/products/", headers=auth_headers)) == {
            "Python Fluente"
        }
        assert titles(client.get("/products/", headers=other_headers)) == {"Clean Code"}

    def test_deleted_alert_no_longer_shows_its_listings(
        self,
        client,
        auth_headers,
        sample_user,
        sample_source_website,
        test_db,
        email_service,
    ):
        add_listing(test_db, sample_source_website, "Python Fluente", 120)
        alert = create_alert(
            client, auth_headers, sample_user, sample_source_website, "python fluente"
        )
        deleted = client.delete(f"/price-alerts/{alert['id']}", headers=auth_headers)
        assert deleted.status_code == 204, deleted.text

        assert titles(client.get("/products/", headers=auth_headers)) == set()

    def test_staff_see_the_whole_catalog(
        self, client, superuser_auth_headers, sample_source_website, test_db
    ):
        add_listing(test_db, sample_source_website, "Anything", 10)
        listed = titles(client.get("/products/", headers=superuser_auth_headers))
        assert "Anything" in listed

    def test_title_filter_ignores_case_and_accents(
        self, client, superuser_auth_headers, sample_source_website, test_db
    ):
        add_listing(test_db, sample_source_website, "Microsserviços prontos", 10)
        add_listing(test_db, sample_source_website, "Outro livro", 10)

        listed = titles(
            client.get(
                "/products/",
                params={"title": "MICROSSERVI"},
                headers=superuser_auth_headers,
            )
        )

        assert listed == {"Microsserviços prontos"}

    def test_opportunities_only(
        self,
        client,
        auth_headers,
        sample_user,
        sample_source_website,
        test_db,
        email_service,
    ):
        add_listing(test_db, sample_source_website, "Clean Code capa dura", 120)
        add_listing(test_db, sample_source_website, "Clean Code bolso", 40)
        create_alert(
            client, auth_headers, sample_user, sample_source_website, "clean code"
        )

        response = client.get(
            "/products/", params={"opportunities_only": True}, headers=auth_headers
        )

        assert titles(response) == {"Clean Code bolso"}
        assert response.json()["meta"]["total"] == 1


# ============================================================================
# C: changing an alert checks the listings already collected
# ============================================================================


class TestAlertChecksCollectedListings:
    def test_raising_max_price_notifies_listings_now_under_it(
        self,
        client,
        auth_headers,
        sample_user,
        sample_source_website,
        test_db,
        email_service,
    ):
        product = add_listing(test_db, sample_source_website, "Fluent Python", 120)
        alert = create_alert(
            client, auth_headers, sample_user, sample_source_website, "fluent python"
        )
        email_service.send_price_alert_email.assert_not_called()

        response = client.put(
            f"/price-alerts/{alert['id']}",
            json=update_body(alert["id"], max_price=150),
            headers=auth_headers,
        )

        assert response.status_code == 200, response.text
        email_service.send_price_alert_email.assert_called_once()
        assert (
            test_db.query(NotificationLogModel)
            .filter_by(price_alert_id=int(alert["id"]), product_id=product.id)
            .count()
            == 1
        )

    def test_new_alert_notifies_listings_already_under_its_price(
        self,
        client,
        auth_headers,
        sample_user,
        sample_source_website,
        test_db,
        email_service,
    ):
        add_listing(test_db, sample_source_website, "Fluent Python barato", 30)
        create_alert(
            client, auth_headers, sample_user, sample_source_website, "fluent python"
        )
        email_service.send_price_alert_email.assert_called_once()

    def test_a_notified_listing_can_still_be_deleted(
        self,
        client,
        auth_headers,
        superuser_auth_headers,
        sample_user,
        sample_source_website,
        test_db,
        email_service,
    ):
        product = add_listing(test_db, sample_source_website, "Fluent Python", 30)
        create_alert(
            client, auth_headers, sample_user, sample_source_website, "fluent python"
        )

        response = client.delete(
            f"/products/{product.id}", headers=superuser_auth_headers
        )

        assert response.status_code == 204, response.text
        logs = test_db.query(NotificationLogModel).all()
        assert len(logs) == 1  # the email history is kept
        assert logs[0].product_id is None

    def test_each_listing_is_notified_once(
        self,
        client,
        auth_headers,
        sample_user,
        sample_source_website,
        test_db,
        email_service,
    ):
        add_listing(test_db, sample_source_website, "Fluent Python barato", 30)
        alert = create_alert(
            client, auth_headers, sample_user, sample_source_website, "fluent python"
        )
        client.put(
            f"/price-alerts/{alert['id']}",
            json=update_body(alert["id"], max_price=60),
            headers=auth_headers,
        )
        assert email_service.send_price_alert_email.call_count == 1

    def test_paused_alert_sends_nothing(
        self,
        client,
        auth_headers,
        sample_user,
        sample_source_website,
        test_db,
        email_service,
    ):
        add_listing(test_db, sample_source_website, "Fluent Python", 120)
        alert = create_alert(
            client, auth_headers, sample_user, sample_source_website, "fluent python"
        )
        client.put(
            f"/price-alerts/{alert['id']}",
            json=update_body(alert["id"], is_active=False, max_price=150),
            headers=auth_headers,
        )
        email_service.send_price_alert_email.assert_not_called()


# ============================================================================
# T: editing an alert respects the plan (it used to be a way around it)
# ============================================================================


class TestEditRespectsPlan:
    def test_cannot_edit_frequency_below_plan_minimum(
        self, client, auth_headers, sample_user, sample_source_website, email_service
    ):
        alert = create_alert(
            client, auth_headers, sample_user, sample_source_website, "ddd"
        )
        response = client.put(
            f"/price-alerts/{alert['id']}",
            json=update_body(alert["id"], frequency_minutes=30),
            headers=auth_headers,
        )
        assert response.status_code == 403
        error = response.json()["errors"][0]
        assert error["code"] == "PLAN_LIMIT_REACHED"
        assert error["meta"] == {
            "limit": "min_frequency_minutes",
            "value": 360,
            "plan": "free",
        }

    def test_cannot_reactivate_beyond_the_alert_limit(
        self, client, auth_headers, sample_user, sample_source_website, email_service
    ):
        paused = create_alert(
            client, auth_headers, sample_user, sample_source_website, "paused one"
        )
        client.put(
            f"/price-alerts/{paused['id']}",
            json=update_body(paused["id"], is_active=False),
            headers=auth_headers,
        )
        for term in ("one", "two", "three"):
            create_alert(client, auth_headers, sample_user, sample_source_website, term)

        response = client.put(
            f"/price-alerts/{paused['id']}",
            json=update_body(paused["id"], is_active=True),
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert response.json()["errors"][0]["meta"]["limit"] == "max_active_alerts"

    def test_editing_price_only_is_not_blocked(
        self, client, auth_headers, sample_user, sample_source_website, email_service
    ):
        alert = create_alert(
            client, auth_headers, sample_user, sample_source_website, "ok"
        )
        response = client.put(
            f"/price-alerts/{alert['id']}",
            json=update_body(alert["id"], max_price=99),
            headers=auth_headers,
        )
        assert response.status_code == 200


# ============================================================================
# A: deleting a search
# ============================================================================


class TestDeleteSearch:
    def test_search_used_by_an_alert_answers_409(
        self,
        client,
        auth_headers,
        superuser_auth_headers,
        sample_user,
        sample_source_website,
        email_service,
    ):
        alert = create_alert(
            client, auth_headers, sample_user, sample_source_website, "in use"
        )
        sc_id = alert["attributes"]["search_config_id"]

        response = client.delete(
            f"/search-configs/{sc_id}", headers=superuser_auth_headers
        )

        assert response.status_code == 409
        error = response.json()["errors"][0]
        assert error["code"] == "SEARCH_CONFIG_IN_USE"
        assert error["meta"] == {"alert_count": 1}

    def test_search_with_run_history_can_be_deleted(
        self,
        client,
        superuser_auth_headers,
        sample_search_config,
        sample_search_execution_log,
        test_db,
    ):
        response = client.delete(
            f"/search-configs/{sample_search_config.id}",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 204
        assert test_db.query(SearchExecutionLogModel).count() == 0

    def test_search_of_a_deleted_alert_can_be_deleted(
        self,
        client,
        auth_headers,
        superuser_auth_headers,
        sample_user,
        sample_source_website,
        email_service,
    ):
        alert = create_alert(
            client, auth_headers, sample_user, sample_source_website, "gone"
        )
        sc_id = alert["attributes"]["search_config_id"]
        client.delete(f"/price-alerts/{alert['id']}", headers=auth_headers)

        response = client.delete(
            f"/search-configs/{sc_id}", headers=superuser_auth_headers
        )
        assert response.status_code == 204

    def test_admin_finds_a_search_by_term(
        self,
        client,
        auth_headers,
        superuser_auth_headers,
        sample_user,
        sample_source_website,
        email_service,
    ):
        create_alert(
            client, auth_headers, sample_user, sample_source_website, "Pocket Book"
        )
        create_alert(client, auth_headers, sample_user, sample_source_website, "other")

        response = client.get(
            "/search-configs/",
            params={"search_term": "pocket"},
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        terms = [i["attributes"]["search_term"] for i in response.json()["data"]]
        assert terms == ["Pocket Book"]
        assert response.json()["meta"]["total"] == 1


# ============================================================================
# B / R: a search run is one log, updated until it finishes
# ============================================================================


class TestSearchRunProgress:
    def test_scraper_reports_progress_and_finish(
        self, client, service_headers, auth_headers, sample_search_config, test_db
    ):
        created = client.post(
            "/search-execution-logs/",
            json={
                "data": {
                    "type": "search_execution_logs",
                    "attributes": {
                        "search_config_id": sample_search_config.id,
                        "status": "running",
                    },
                }
            },
            headers=service_headers,
        )
        log_id = created.json()["data"]["id"]

        def patch_log(**attributes):
            response = client.patch(
                f"/search-execution-logs/{log_id}",
                json={
                    "data": {
                        "type": "search_execution_logs",
                        "id": log_id,
                        "attributes": attributes,
                    }
                },
                headers=service_headers,
            )
            assert response.status_code == 200, response.text
            return response.json()["data"]["attributes"]

        progress = patch_log(listings_found=12, listings_checked=5, results_count=1)
        assert progress["status"] == "running"
        assert progress["finished_at"] is None

        done = patch_log(status="success", listings_checked=12, results_count=3)
        assert done["finished_at"] is not None

        status = client.get(
            f"/search-configs/{sample_search_config.id}/execution-status",
            headers=auth_headers,
        ).json()["data"]["attributes"]
        assert status["status"] == "success"
        assert status["listings_found"] == 12
        assert status["listings_checked"] == 12
        assert status["results_count"] == 3

    def test_customers_cannot_write_run_logs(
        self, client, auth_headers, sample_search_execution_log
    ):
        response = client.patch(
            f"/search-execution-logs/{sample_search_execution_log.id}",
            json={
                "data": {
                    "type": "search_execution_logs",
                    "attributes": {"status": "failed"},
                }
            },
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_a_lost_run_is_closed_instead_of_blocking_forever(
        self, client, auth_headers, sample_search_config, test_db
    ):
        test_db.add(
            SearchExecutionLogModel(
                search_config_id=sample_search_config.id,
                status="running",
                started_at=datetime.now(UTC) - timedelta(hours=2),
            )
        )
        test_db.commit()

        status = client.get(
            f"/search-configs/{sample_search_config.id}/execution-status",
            headers=auth_headers,
        ).json()["data"]["attributes"]

        assert status["status"] == "failed"
        assert status["finished_at"] is not None
