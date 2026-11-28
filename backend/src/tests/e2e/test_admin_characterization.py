"""Characterization tests before the admin module.

They pin today's behavior of `GET /admin/summary` and
`POST /admin/cleanup-products` over HTTP, so the refactor that gives the
admin its own module (behind the other modules' use cases instead of their
ORM models) can prove it changed nothing. Each test kills a mutation that
survived the existing suite (Nov 28, 2026).
"""

from datetime import UTC, datetime, timedelta

from src.app.accounts.persistence.models import User as UserModel
from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.alerts.persistence.models import price_alert_source_website
from src.app.catalog.entities import ProductCondition
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.searches.persistence.models import SavedSearch as SavedSearchModel
from src.app.searches.persistence.models import SearchRun as SearchRunModel
from src.app.stores.persistence.models import Store as StoreModel

START = datetime(2026, 1, 1, 12, 0, 0)


def add(test_db, *rows):
    test_db.add_all(rows)
    test_db.commit()
    for row in rows:
        test_db.refresh(row)
    return rows[0] if len(rows) == 1 else rows


def add_alert(test_db, user_id, search_term="phone", store=None, **fields):
    alert = add(
        test_db,
        PriceAlertModel(
            search_term=search_term,
            max_price=fields.pop("max_price", 500.0),
            is_active=fields.pop("is_active", True),
            frequency_minutes=60,
            user_id=user_id,
            **fields,
        ),
    )
    if store is not None:
        test_db.execute(
            price_alert_source_website.insert().values(
                price_alert_id=alert.id, source_website_id=store.id
            )
        )
        test_db.commit()
    return alert


def add_product(test_db, store, title, days_old=5, **fields):
    """Add a product and return its id (the row may be gone after a cleanup)."""
    product = add(
        test_db,
        ProductModel(
            url=f"https://{store.name.lower().replace(' ', '-')}.example.com/"
            f"{title.lower().replace(' ', '-')}",
            title=title,
            condition=ProductCondition.NEW,
            is_available=fields.pop("is_available", True),
            source_website_id=store.id,
            updated_at=datetime.now(UTC) - timedelta(days=days_old),
            **fields,
        ),
    )
    return product.id


def add_runs(test_db, *runs):
    search = add(test_db, SavedSearchModel(search_term="phone"))
    return add(
        test_db,
        *[SearchRunModel(search_config_id=search.id, **run) for run in runs],
    )


def summary(client, headers):
    response = client.get("/admin/summary", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]["attributes"]


def cleanup(client, headers, **params):
    response = client.post("/admin/cleanup-products", params=params, headers=headers)
    assert response.status_code == 200
    return response.json()["data"]["attributes"]


def product_exists(test_db, product_id):
    test_db.expire_all()
    return test_db.get(ProductModel, product_id) is not None


class TestAdminSummary:
    def test_a_staff_user_cannot_read_the_summary(self, client, staff_auth_headers):
        response = client.get("/admin/summary", headers=staff_auth_headers)

        assert response.status_code == 403

    def test_counts_all_users_and_the_active_ones(
        self, client, superuser_auth_headers, test_db
    ):
        add(
            test_db,
            UserModel(
                username="gone",
                email="gone@example.com",
                hashed_password="x",
                is_active=False,
            ),
        )

        attributes = summary(client, superuser_auth_headers)

        assert attributes["total-users"] == 2
        assert attributes["active-users"] == 1

    def test_alert_counts_leave_out_soft_deleted_alerts(
        self, client, superuser_auth_headers, test_db, sample_superuser
    ):
        user_id = sample_superuser.id
        add_alert(test_db, user_id, "active")
        add_alert(test_db, user_id, "paused", is_active=False)
        add_alert(test_db, user_id, "deleted", deleted_at=datetime.now(UTC))
        add_alert(
            test_db,
            user_id,
            "deleted and paused",
            is_active=False,
            deleted_at=datetime.now(UTC),
        )

        attributes = summary(client, superuser_auth_headers)

        assert attributes["total-alerts"] == 2
        assert attributes["active-alerts"] == 1

    def test_counts_every_product_available_or_not(
        self, client, superuser_auth_headers, test_db, sample_store
    ):
        add_product(test_db, sample_store, "In stock")
        add_product(test_db, sample_store, "Sold out", is_available=False)

        assert summary(client, superuser_auth_headers)["total-products"] == 2

    def test_counts_all_stores_and_the_active_ones(
        self, client, superuser_auth_headers, test_db, sample_store
    ):
        add(
            test_db,
            StoreModel(
                name="Closed", base_url="https://closed.example.com", is_active=False
            ),
        )

        attributes = summary(client, superuser_auth_headers)

        assert attributes["total-source-websites"] == 2
        assert attributes["active-source-websites"] == 1

    def test_recent_executions_are_the_latest_20_runs_newest_first(
        self, client, superuser_auth_headers, test_db
    ):
        runs = add_runs(
            test_db,
            *[
                {"status": "success", "started_at": START + timedelta(minutes=i)}
                for i in range(21)
            ],
        )

        executions = summary(client, superuser_auth_headers)["recent-executions"]

        assert [e["id"] for e in executions] == [run.id for run in runs[:0:-1]]

    def test_scraper_stats_count_successes_and_failures_among_recent_runs(
        self, client, superuser_auth_headers, test_db
    ):
        add_runs(
            test_db,
            {"status": "success", "started_at": START},
            {"status": "success", "started_at": START + timedelta(minutes=1)},
            {"status": "failed", "started_at": START + timedelta(minutes=2)},
            {"status": "running", "started_at": START + timedelta(minutes=3)},
        )

        stats = summary(client, superuser_auth_headers)["scraper-stats"]

        assert stats == {"recent-total": 4, "success-count": 2, "failed-count": 1}

    def test_a_recent_execution_shows_the_run_as_stored(
        self, client, superuser_auth_headers, test_db
    ):
        run = add_runs(
            test_db,
            {
                "status": "failed",
                "results_count": 3,
                "error_message": "store timed out",
                "started_at": START,
                "finished_at": START + timedelta(minutes=2),
            },
        )

        [execution] = summary(client, superuser_auth_headers)["recent-executions"]

        assert execution == {
            "id": run.id,
            "search-config-id": run.search_config_id,
            "status": "failed",
            "results-count": 3,
            "error-message": "store timed out",
            "started-at": "2026-01-01T12:00:00",
            "finished-at": "2026-01-01T12:02:00",
        }


class TestCleanupProducts:
    def test_keeps_a_product_newer_than_days_old(
        self, client, superuser_auth_headers, test_db, sample_store
    ):
        recent = add_product(test_db, sample_store, "Recent listing", days_old=0)
        old = add_product(test_db, sample_store, "Old listing", days_old=5)

        attributes = cleanup(client, superuser_auth_headers, days_old=1)

        assert attributes["deleted-count"] == 1
        assert product_exists(test_db, recent)
        assert not product_exists(test_db, old)

    def test_days_old_defaults_to_30(
        self, client, superuser_auth_headers, test_db, sample_store
    ):
        month_old = add_product(test_db, sample_store, "Month old", days_old=29)
        older = add_product(test_db, sample_store, "Older", days_old=31)

        cleanup(client, superuser_auth_headers)

        assert product_exists(test_db, month_old)
        assert not product_exists(test_db, older)

    def test_keeps_a_product_an_active_alert_finds(
        self, client, superuser_auth_headers, test_db, sample_superuser, sample_store
    ):
        add_alert(test_db, sample_superuser.id, "phone", store=sample_store)
        found = add_product(test_db, sample_store, "Great Phone Deal")

        attributes = cleanup(client, superuser_auth_headers, days_old=1)

        assert attributes["eligible-count"] == 0
        assert product_exists(test_db, found)

    def test_a_paused_alert_does_not_keep_a_product(
        self, client, superuser_auth_headers, test_db, sample_superuser, sample_store
    ):
        add_alert(
            test_db, sample_superuser.id, "phone", store=sample_store, is_active=False
        )
        product = add_product(test_db, sample_store, "Great Phone Deal")

        cleanup(client, superuser_auth_headers, days_old=1)

        assert not product_exists(test_db, product)

    def test_a_soft_deleted_alert_does_not_keep_a_product(
        self, client, superuser_auth_headers, test_db, sample_superuser, sample_store
    ):
        add_alert(
            test_db,
            sample_superuser.id,
            "phone",
            store=sample_store,
            deleted_at=datetime.now(UTC),
        )
        product = add_product(test_db, sample_store, "Great Phone Deal")

        cleanup(client, superuser_auth_headers, days_old=1)

        assert not product_exists(test_db, product)

    def test_an_alert_keeps_only_products_whose_title_has_its_term(
        self, client, superuser_auth_headers, test_db, sample_superuser, sample_store
    ):
        add_alert(test_db, sample_superuser.id, "phone", store=sample_store)
        other = add_product(test_db, sample_store, "Garden Chair")

        cleanup(client, superuser_auth_headers, days_old=1)

        assert not product_exists(test_db, other)

    def test_an_alert_keeps_only_products_from_its_stores(
        self, client, superuser_auth_headers, test_db, sample_superuser, sample_store
    ):
        elsewhere = add(
            test_db,
            StoreModel(name="Elsewhere", base_url="https://elsewhere.example.com"),
        )
        add_alert(test_db, sample_superuser.id, "phone", store=sample_store)
        product = add_product(test_db, elsewhere, "Great Phone Deal")

        cleanup(client, superuser_auth_headers, days_old=1)

        assert not product_exists(test_db, product)
