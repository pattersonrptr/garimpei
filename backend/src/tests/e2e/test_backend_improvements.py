"""
E2E Tests for Backend Improvements (Issue #42)

Tests:
- Soft delete on PriceAlerts
- GET /dashboard/summary
- GET /price-alerts/{id}/opportunities
- POST /admin/cleanup-products
"""

from datetime import UTC, datetime, timedelta

from src.app.alerts.persistence.models import (
    PriceAlert as PriceAlertModel,
)
from src.app.alerts.persistence.models import (
    price_alert_source_website,
)
from src.app.catalog.entities import ProductCondition
from src.app.catalog.persistence.models import (
    PriceHistory as PriceHistoryModel,
)
from src.app.catalog.persistence.models import (
    Product as ProductModel,
)
from src.app.infrastructure.database.models.search_config_model import (
    SearchConfig as SearchConfigModel,
)
from src.app.infrastructure.database.models.search_execution_log_model import (
    SearchExecutionLog as SearchExecutionLogModel,
)

# ============================================================================
# JSON:API payload helpers
# ============================================================================

ALERT_TYPE = "price_alert"


def make_alert_payload(**overrides):
    attrs = {
        "search_term": "test phone",
        "max_price": 500.0,
        "is_active": True,
        "frequency_minutes": 60,
        "source_website_ids": [],
        **overrides,
    }
    return {"data": {"type": ALERT_TYPE, "attributes": attrs}}


# ============================================================================
# Soft Delete — DELETE /price-alerts/{id}
# ============================================================================


class TestPriceAlertSoftDelete:
    """Test that DELETE /price-alerts/{id} performs a soft delete."""

    def test_delete_sets_deleted_at(
        self,
        client,
        staff_auth_headers,
        test_db,
        sample_staff_user,
        sample_source_website,
    ):
        """
        Given: An existing active price alert
        When: DELETE /price-alerts/{id}
        Then: The alert is soft-deleted (deleted_at set, is_active=False), not removed from DB
        """
        config = SearchConfigModel(
            search_term="laptop",
            is_active=True,
            frequency_days=1,
            user_id=sample_staff_user.id,
        )
        test_db.add(config)
        test_db.commit()
        test_db.refresh(config)

        alert = PriceAlertModel(
            search_term="laptop",
            max_price=1000.0,
            is_active=True,
            frequency_minutes=30,
            user_id=sample_staff_user.id,
            search_config_id=config.id,
        )
        test_db.add(alert)
        test_db.commit()
        test_db.refresh(alert)

        response = client.delete(
            f"/price-alerts/{alert.id}", headers=staff_auth_headers
        )
        assert response.status_code == 204

        # Verify soft delete in DB
        test_db.expire_all()
        db_alert = (
            test_db.query(PriceAlertModel)
            .filter(PriceAlertModel.id == alert.id)
            .first()
        )
        assert db_alert is not None, "Record should still exist in DB"
        assert db_alert.deleted_at is not None
        assert db_alert.is_active is False

    def test_soft_deleted_alert_not_returned_by_get(
        self, client, staff_auth_headers, test_db, sample_staff_user
    ):
        """
        Given: A soft-deleted price alert
        When: GET /price-alerts/{id}
        Then: Returns 404
        """
        alert = PriceAlertModel(
            search_term="tablet",
            max_price=300.0,
            is_active=False,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
            deleted_at=datetime.now(UTC),
        )
        test_db.add(alert)
        test_db.commit()
        test_db.refresh(alert)

        response = client.get(f"/price-alerts/{alert.id}", headers=staff_auth_headers)
        assert response.status_code == 404

    def test_soft_deleted_alert_excluded_from_list(
        self, client, staff_auth_headers, test_db, sample_staff_user
    ):
        """
        Given: One active and one soft-deleted alert
        When: GET /price-alerts/
        Then: Only the active alert is returned
        """
        active = PriceAlertModel(
            search_term="active item",
            max_price=100.0,
            is_active=True,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
        )
        deleted = PriceAlertModel(
            search_term="deleted item",
            max_price=200.0,
            is_active=False,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
            deleted_at=datetime.now(UTC),
        )
        test_db.add_all([active, deleted])
        test_db.commit()

        response = client.get("/price-alerts/", headers=staff_auth_headers)
        assert response.status_code == 200
        items = response.json()["data"]
        search_terms = [item["attributes"]["search_term"] for item in items]
        assert "active item" in search_terms
        assert "deleted item" not in search_terms


# ============================================================================
# GET /dashboard/summary
# ============================================================================


class TestDashboardSummary:
    """Test GET /dashboard/summary endpoint."""

    def test_returns_summary_for_authenticated_user(
        self,
        client,
        staff_auth_headers,
        test_db,
        sample_staff_user,
        sample_source_website,
    ):
        """
        Given: A staff user with alerts and matching products
        When: GET /dashboard/summary
        Then: Returns aggregated dashboard data
        """
        # Create search config
        config = SearchConfigModel(
            search_term="phone",
            is_active=True,
            frequency_days=1,
            user_id=sample_staff_user.id,
        )
        test_db.add(config)
        test_db.commit()
        test_db.refresh(config)

        # Create alert
        alert = PriceAlertModel(
            search_term="phone",
            max_price=500.0,
            is_active=True,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
            search_config_id=config.id,
        )
        test_db.add(alert)
        test_db.commit()
        test_db.refresh(alert)

        # Link source website to alert
        test_db.execute(
            price_alert_source_website.insert().values(
                price_alert_id=alert.id,
                source_website_id=sample_source_website.id,
            )
        )
        test_db.commit()

        # Create a matching product with price history
        product = ProductModel(
            url="https://test.example.com/phone/1",
            title="Great Phone Deal",
            condition=ProductCondition.NEW,
            is_available=True,
            source_website_id=sample_source_website.id,
        )
        test_db.add(product)
        test_db.commit()
        test_db.refresh(product)

        test_db.add(PriceHistoryModel(product_id=product.id, price=300.0))
        test_db.commit()

        # Create execution log
        log = SearchExecutionLogModel(
            search_config_id=config.id,
            status="success",
            results_count=1,
            started_at=datetime.now(UTC) - timedelta(minutes=30),
            finished_at=datetime.now(UTC) - timedelta(minutes=29),
        )
        test_db.add(log)
        test_db.commit()

        response = client.get("/dashboard/summary", headers=staff_auth_headers)
        assert response.status_code == 200

        data = response.json()["data"]
        assert data["type"] == "dashboard-summary"
        attrs = data["attributes"]
        assert attrs["active-alerts"] == 1
        assert attrs["total-alerts"] == 1
        assert isinstance(attrs["recent-opportunities"], list)
        assert isinstance(attrs["next-checks"], list)
        assert len(attrs["next-checks"]) == 1

    def test_excludes_soft_deleted_alerts(
        self, client, staff_auth_headers, test_db, sample_staff_user
    ):
        """
        Given: One active and one soft-deleted alert
        When: GET /dashboard/summary
        Then: Only counts non-deleted alerts
        """
        active = PriceAlertModel(
            search_term="watch",
            max_price=200.0,
            is_active=True,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
        )
        deleted = PriceAlertModel(
            search_term="old watch",
            max_price=100.0,
            is_active=False,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
            deleted_at=datetime.now(UTC),
        )
        test_db.add_all([active, deleted])
        test_db.commit()

        response = client.get("/dashboard/summary", headers=staff_auth_headers)
        assert response.status_code == 200
        attrs = response.json()["data"]["attributes"]
        assert attrs["total-alerts"] == 1
        assert attrs["active-alerts"] == 1

    def test_requires_authentication(self, client):
        """
        Given: No auth token
        When: GET /dashboard/summary
        Then: Returns 401 or 403
        """
        response = client.get("/dashboard/summary")
        assert response.status_code in (401, 403)


# ============================================================================
# GET /price-alerts/{id}/opportunities
# ============================================================================


class TestOpportunitiesEndpoint:
    """Test GET /price-alerts/{id}/opportunities endpoint."""

    def test_returns_matching_products_within_max_price(
        self,
        client,
        staff_auth_headers,
        test_db,
        sample_staff_user,
        sample_source_website,
    ):
        """
        Given: An alert with max_price=500 and products at various prices
        When: GET /price-alerts/{id}/opportunities
        Then: Only returns products at or below max_price
        """
        config = SearchConfigModel(
            search_term="headphones",
            is_active=True,
            frequency_days=1,
            user_id=sample_staff_user.id,
        )
        test_db.add(config)
        test_db.commit()
        test_db.refresh(config)

        alert = PriceAlertModel(
            search_term="headphones",
            max_price=500.0,
            is_active=True,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
            search_config_id=config.id,
        )
        test_db.add(alert)
        test_db.commit()
        test_db.refresh(alert)

        # Link source website
        test_db.execute(
            price_alert_source_website.insert().values(
                price_alert_id=alert.id,
                source_website_id=sample_source_website.id,
            )
        )
        test_db.commit()

        # Create products
        cheap = ProductModel(
            url="https://test.example.com/headphones/cheap",
            title="Budget Headphones",
            condition=ProductCondition.NEW,
            is_available=True,
            source_website_id=sample_source_website.id,
        )
        expensive = ProductModel(
            url="https://test.example.com/headphones/expensive",
            title="Premium Headphones",
            condition=ProductCondition.NEW,
            is_available=True,
            source_website_id=sample_source_website.id,
        )
        test_db.add_all([cheap, expensive])
        test_db.commit()
        test_db.refresh(cheap)
        test_db.refresh(expensive)

        # Add price history
        test_db.add(PriceHistoryModel(product_id=cheap.id, price=200.0))
        test_db.add(PriceHistoryModel(product_id=expensive.id, price=800.0))
        test_db.commit()

        response = client.get(
            f"/price-alerts/{alert.id}/opportunities",
            headers=staff_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        # Only the cheap product should match (200 <= 500)
        assert len(data) == 1
        assert data[0]["attributes"]["title"] == "Budget Headphones"

    def test_returns_404_for_nonexistent_alert(self, client, staff_auth_headers):
        """
        Given: A non-existent alert ID
        When: GET /price-alerts/9999/opportunities
        Then: Returns 404
        """
        response = client.get(
            "/price-alerts/9999/opportunities", headers=staff_auth_headers
        )
        assert response.status_code == 404

    def test_supports_pagination(
        self,
        client,
        staff_auth_headers,
        test_db,
        sample_staff_user,
        sample_source_website,
    ):
        """
        Given: An alert with multiple matching products
        When: GET /price-alerts/{id}/opportunities?limit=1&offset=0
        Then: Returns paginated results
        """
        config = SearchConfigModel(
            search_term="earbuds",
            is_active=True,
            frequency_days=1,
            user_id=sample_staff_user.id,
        )
        test_db.add(config)
        test_db.commit()
        test_db.refresh(config)

        alert = PriceAlertModel(
            search_term="earbuds",
            max_price=1000.0,
            is_active=True,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
            search_config_id=config.id,
        )
        test_db.add(alert)
        test_db.commit()
        test_db.refresh(alert)

        test_db.execute(
            price_alert_source_website.insert().values(
                price_alert_id=alert.id,
                source_website_id=sample_source_website.id,
            )
        )
        test_db.commit()

        for i in range(3):
            p = ProductModel(
                url=f"https://test.example.com/earbuds/{i}",
                title=f"Earbuds Model {i}",
                condition=ProductCondition.NEW,
                is_available=True,
                source_website_id=sample_source_website.id,
            )
            test_db.add(p)
            test_db.commit()
            test_db.refresh(p)
            test_db.add(PriceHistoryModel(product_id=p.id, price=100.0 + i * 50))
        test_db.commit()

        response = client.get(
            f"/price-alerts/{alert.id}/opportunities?limit=1&offset=0",
            headers=staff_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        meta = response.json().get("meta", {})
        assert meta.get("total", 0) >= 1


# ============================================================================
# POST /admin/cleanup-products
# ============================================================================


class TestCleanupProducts:
    """Test POST /admin/cleanup-products endpoint."""

    def test_dry_run_returns_eligible_count(
        self, client, superuser_auth_headers, test_db, sample_source_website
    ):
        """
        Given: Old orphaned products
        When: POST /admin/cleanup-products?dry_run=true&days_old=1
        Then: Returns eligible count without deleting
        """
        old_product = ProductModel(
            url="https://test.example.com/old",
            title="Orphaned Old Product",
            condition=ProductCondition.NEW,
            is_available=True,
            source_website_id=sample_source_website.id,
            updated_at=datetime.now(UTC) - timedelta(days=5),
        )
        test_db.add(old_product)
        test_db.commit()

        response = client.post(
            "/admin/cleanup-products?dry_run=true&days_old=1",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        attrs = response.json()["data"]["attributes"]
        assert attrs["dry-run"] is True
        assert attrs["eligible-count"] >= 1
        assert attrs["deleted-count"] == 0

        # Product should still exist
        test_db.expire_all()
        still_exists = (
            test_db.query(ProductModel)
            .filter(ProductModel.id == old_product.id)
            .first()
        )
        assert still_exists is not None

    def test_cleanup_deletes_orphaned_products(
        self, client, superuser_auth_headers, test_db, sample_source_website
    ):
        """
        Given: Old orphaned products
        When: POST /admin/cleanup-products?days_old=1
        Then: Deletes products not matching any active alert
        """
        old_product = ProductModel(
            url="https://test.example.com/orphan",
            title="Orphaned Product",
            condition=ProductCondition.NEW,
            is_available=True,
            source_website_id=sample_source_website.id,
            updated_at=datetime.now(UTC) - timedelta(days=5),
        )
        test_db.add(old_product)
        test_db.commit()
        product_id = old_product.id

        response = client.post(
            "/admin/cleanup-products?days_old=1",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        attrs = response.json()["data"]["attributes"]
        assert attrs["dry-run"] is False
        assert attrs["deleted-count"] >= 1

        test_db.expire_all()
        gone = test_db.query(ProductModel).filter(ProductModel.id == product_id).first()
        assert gone is None

    def test_requires_superuser(self, client, staff_auth_headers):
        """
        Given: A staff (non-superuser) token
        When: POST /admin/cleanup-products
        Then: Returns 403
        """
        response = client.post("/admin/cleanup-products", headers=staff_auth_headers)
        assert response.status_code == 403
