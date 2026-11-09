"""
E2E Tests for POST /products/{id}/evaluate-alerts

Tests the complete flow:
    HTTP Request → ProductController → EvaluateProductAlertsUseCase
    → repos (PriceAlert, NotificationLog, PriceHistory, Product) → Database

Email service is mocked to avoid external calls.
"""

from unittest.mock import MagicMock

from src.app.catalog.entities import ProductCondition
from src.app.catalog.http.product_controller import get_email_service
from src.app.interfaces.services.email_service import EmailResult
from src.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _override_email_service(success=True, error_message=None):
    """Return a dependency override that returns a mock email service."""
    mock_svc = MagicMock()
    mock_svc.send_price_alert_email.return_value = EmailResult(
        success=success,
        status_code=202 if success else 500,
        error_message=error_message,
    )

    def override():
        return mock_svc

    return override, mock_svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEvaluateProductAlerts:
    """POST /products/{product_id}/evaluate-alerts"""

    def test_returns_404_when_product_not_found(self, client, staff_auth_headers):
        """
        Given: No product with ID 9999 exists
        When: POST /products/9999/evaluate-alerts
        Then: Returns 404
        """
        response = client.post(
            "/products/9999/evaluate-alerts",
            headers=staff_auth_headers,
        )
        assert response.status_code == 404

    def test_returns_skipped_when_product_has_no_price(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: A product exists but has no price_history
        When: POST /products/{id}/evaluate-alerts
        Then: Returns 200 with status=skipped, message about no price
        """
        response = client.post(
            f"/products/{sample_product.id}/evaluate-alerts",
            headers=staff_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]["attributes"]
        assert data["status"] == "skipped"
        assert "no price" in data["message"].lower()

    def test_returns_skipped_when_no_matching_alerts(
        self, client, staff_auth_headers, test_db, sample_product
    ):
        """
        Given: A product with a price but no matching price alerts
        When: POST /products/{id}/evaluate-alerts
        Then: Returns 200 with status=skipped, no matching alerts
        """
        from src.app.catalog.persistence.models import (
            PriceHistory as PriceHistoryModel,
        )

        ph = PriceHistoryModel(product_id=sample_product.id, price=100.00)
        test_db.add(ph)
        test_db.commit()

        response = client.post(
            f"/products/{sample_product.id}/evaluate-alerts",
            headers=staff_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]["attributes"]
        assert data["status"] == "skipped"
        assert "no matching alerts" in data["message"].lower()

    def test_sends_notification_for_matching_alert(
        self,
        client,
        staff_auth_headers,
        test_db,
        sample_source_website,
        sample_staff_user,
    ):
        """
        Given: A product with price + matching active alert
        When: POST /products/{id}/evaluate-alerts
        Then: Returns 200 with notifications_sent=1
        """
        from src.app.catalog.persistence.models import (
            PriceHistory as PriceHistoryModel,
        )
        from src.app.catalog.persistence.models import (
            Product as ProductModel,
        )
        from src.app.infrastructure.database.models.price_alert_model import (
            PriceAlert as PriceAlertModel,
        )

        # Create product with title matching alert search_term
        product = ProductModel(
            url="https://test.example.com/iphone-13",
            title="iPhone 13 128GB Preto",
            condition=ProductCondition.USED,
            is_available=True,
            source_website_id=sample_source_website.id,
        )
        test_db.add(product)
        test_db.flush()

        # Add price history
        ph = PriceHistoryModel(product_id=product.id, price=2000.00)
        test_db.add(ph)
        test_db.flush()

        # Create a matching price alert
        alert = PriceAlertModel(
            search_term="iPhone 13",
            max_price=2500.00,
            is_active=True,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
        )
        test_db.add(alert)
        test_db.flush()

        # Add alert ↔ source_website M2M
        alert.source_websites.append(sample_source_website)
        test_db.commit()

        # Mock email service
        override, mock_svc = _override_email_service(success=True)
        app.dependency_overrides[get_email_service] = override

        try:
            response = client.post(
                f"/products/{product.id}/evaluate-alerts",
                headers=staff_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]["attributes"]
            assert data["status"] == "sent"
            assert data["notifications_sent"] == 1
            assert data["skipped"] == 0

            # Email service was called
            mock_svc.send_price_alert_email.assert_called_once()
            call_kwargs = mock_svc.send_price_alert_email.call_args[1]
            assert call_kwargs["search_term"] == "iPhone 13"
            assert call_kwargs["product_price"] == 2000.00
        finally:
            app.dependency_overrides.pop(get_email_service, None)

    def test_dedup_skips_already_notified_alert(
        self,
        client,
        staff_auth_headers,
        test_db,
        sample_source_website,
        sample_staff_user,
    ):
        """
        Given: A matching alert that was already notified for this product
        When: POST /products/{id}/evaluate-alerts (second call)
        Then: Returns 200 with skipped=1, notifications_sent=0
        """
        from src.app.catalog.persistence.models import (
            PriceHistory as PriceHistoryModel,
        )
        from src.app.catalog.persistence.models import (
            Product as ProductModel,
        )
        from src.app.infrastructure.database.models.notification_log_model import (
            NotificationLog as NotificationLogModel,
        )
        from src.app.infrastructure.database.models.price_alert_model import (
            PriceAlert as PriceAlertModel,
        )

        product = ProductModel(
            url="https://test.example.com/galaxy-s24",
            title="Galaxy S24 Ultra",
            condition=ProductCondition.NEW,
            is_available=True,
            source_website_id=sample_source_website.id,
        )
        test_db.add(product)
        test_db.flush()

        ph = PriceHistoryModel(product_id=product.id, price=3000.00)
        test_db.add(ph)
        test_db.flush()

        alert = PriceAlertModel(
            search_term="Galaxy S24",
            max_price=4000.00,
            is_active=True,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
        )
        test_db.add(alert)
        test_db.flush()
        alert.source_websites.append(sample_source_website)
        test_db.flush()

        # Pre-existing notification log for this alert + product
        existing_log = NotificationLogModel(
            price_alert_id=alert.id,
            user_id=sample_staff_user.id,
            product_id=product.id,
            email_to=sample_staff_user.email,
            subject="Previous notification",
            status="sent",
        )
        test_db.add(existing_log)
        test_db.commit()

        override, mock_svc = _override_email_service(success=True)
        app.dependency_overrides[get_email_service] = override

        try:
            response = client.post(
                f"/products/{product.id}/evaluate-alerts",
                headers=staff_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()["data"]["attributes"]
            assert data["notifications_sent"] == 0
            assert data["skipped"] == 1

            # Email service should NOT have been called
            mock_svc.send_price_alert_email.assert_not_called()
        finally:
            app.dependency_overrides.pop(get_email_service, None)

    def test_requires_staff_auth(self, client, auth_headers, sample_product):
        """
        Given: A regular (non-staff) user
        When: POST /products/{id}/evaluate-alerts
        Then: Returns 403
        """
        response = client.post(
            f"/products/{sample_product.id}/evaluate-alerts",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_skips_alerts_with_price_above_max(
        self,
        client,
        staff_auth_headers,
        test_db,
        sample_source_website,
        sample_staff_user,
    ):
        """
        Given: Product price is above the alert's max_price
        When: POST /products/{id}/evaluate-alerts
        Then: No matching alerts, returns skipped
        """
        from src.app.catalog.persistence.models import (
            PriceHistory as PriceHistoryModel,
        )
        from src.app.catalog.persistence.models import (
            Product as ProductModel,
        )
        from src.app.infrastructure.database.models.price_alert_model import (
            PriceAlert as PriceAlertModel,
        )

        product = ProductModel(
            url="https://test.example.com/expensive",
            title="iPhone 15 Pro Max",
            condition=ProductCondition.NEW,
            is_available=True,
            source_website_id=sample_source_website.id,
        )
        test_db.add(product)
        test_db.flush()

        ph = PriceHistoryModel(product_id=product.id, price=8000.00)
        test_db.add(ph)
        test_db.flush()

        alert = PriceAlertModel(
            search_term="iPhone 15",
            max_price=5000.00,  # Below product price
            is_active=True,
            frequency_minutes=60,
            user_id=sample_staff_user.id,
        )
        test_db.add(alert)
        test_db.flush()
        alert.source_websites.append(sample_source_website)
        test_db.commit()

        response = client.post(
            f"/products/{product.id}/evaluate-alerts",
            headers=staff_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()["data"]["attributes"]
        assert data["status"] == "skipped"
        assert data["notifications_sent"] == 0
