"""
Unit tests for EvaluateProductAlertsUseCase.

Tests all code paths with mocked repositories and email service:
- Product not found
- No price history
- No matching alerts
- Dedup: alert already notified for product
- Success: email sent + log created
- Email failure: log with status='failed'
- Multiple alerts: mix of sent, skipped, failed
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from src.app.alerts.entities import Listing
from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.use_cases import (
    EvaluateProductAlertsUseCase,
)
from src.app.entities.source_website import SourceWebsite as SourceWebsiteEntity
from src.app.entities.user import User as UserEntity
from src.app.interfaces.services.email_service import EmailResult

# ============================================================================
# Helpers
# ============================================================================


def make_listing(**overrides):
    """A listing with its latest price (2000.00 unless given)."""
    defaults = {
        "id": 100,
        "url": "https://example.com/product/1",
        "title": "iPhone 13 128GB Preto",
        "store_id": 1,
        "price": 2000.00,
        "condition": "undetermined",
        "is_available": True,
    }
    defaults.update(overrides)
    return Listing(**defaults)


def make_price_alert(**overrides):
    defaults = {
        "id": 10,
        "search_term": "iPhone 13",
        "max_price": 2500.00,
        "is_active": True,
        "frequency_minutes": 60,
        "user_id": 1,
        "search_config_id": 5,
        "source_website_ids": [1, 2],
        "created_at": datetime(2024, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2024, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return PriceAlertEntity(**defaults)


def make_user(**overrides):
    defaults = {
        "id": 1,
        "username": "testuser",
        "email": "user@example.com",
        "hashed_password": "hashed",
        "is_active": True,
    }
    defaults.update(overrides)
    return UserEntity(**defaults)


def make_source_website(**overrides):
    defaults = {
        "id": 1,
        "name": "Mercado Livre",
        "base_url": "https://www.mercadolivre.com.br",
        "is_active": True,
    }
    defaults.update(overrides)
    return SourceWebsiteEntity(**defaults)


# ============================================================================
# Test class
# ============================================================================


class TestEvaluateProductAlertsUseCase:
    def _build_use_case(
        self,
        product_repo=None,
        price_alert_repo=None,
        notification_log_repo=None,
        user_repo=None,
        source_website_repo=None,
        email_service=None,
    ):
        return EvaluateProductAlertsUseCase(
            listings=product_repo or MagicMock(),
            price_alert_repo=price_alert_repo or MagicMock(),
            notification_log_repo=notification_log_repo or MagicMock(),
            owners=user_repo or MagicMock(),
            stores=source_website_repo or MagicMock(),
            mailer=email_service or MagicMock(),
        )

    # ------------------------------------------------------------------
    # Early exit paths
    # ------------------------------------------------------------------

    def test_returns_error_when_product_not_found(self):
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = None

        uc = self._build_use_case(product_repo=prod_repo)
        sent, skipped, error = uc.execute(999)

        assert sent == []
        assert skipped == 0
        assert error == "Product not found"

    def test_returns_error_when_no_price_history(self):
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = make_listing(price=None)

        uc = self._build_use_case(product_repo=prod_repo)
        sent, skipped, error = uc.execute(100)

        assert sent == []
        assert skipped == 0
        assert error == "Product has no price history"

    def test_returns_error_when_no_matching_alerts(self):
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = make_listing()

        pa_repo = MagicMock()
        pa_repo.find_matching_alerts_for_product.return_value = []

        uc = self._build_use_case(
            product_repo=prod_repo,
            price_alert_repo=pa_repo,
        )
        sent, skipped, error = uc.execute(100)

        assert sent == []
        assert skipped == 0
        assert error == "No matching alerts found"

    # ------------------------------------------------------------------
    # Dedup check
    # ------------------------------------------------------------------

    def test_skips_already_notified_alert(self):
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = make_listing()

        pa_repo = MagicMock()
        pa_repo.find_matching_alerts_for_product.return_value = [make_price_alert()]

        nl_repo = MagicMock()
        nl_repo.exists_for_alert_and_product.return_value = True  # Already notified

        sw_repo = MagicMock()
        sw_repo.get_by_id.return_value = make_source_website()

        uc = self._build_use_case(
            product_repo=prod_repo,
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
            source_website_repo=sw_repo,
        )
        sent, skipped, error = uc.execute(100)

        assert sent == []
        assert skipped == 1
        assert error is None
        nl_repo.exists_for_alert_and_product.assert_called_once_with(
            price_alert_id=10, product_id=100
        )

    # ------------------------------------------------------------------
    # Success path
    # ------------------------------------------------------------------

    def test_sends_email_and_creates_log_on_success(self):
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = make_listing(price=2000.00)

        pa_repo = MagicMock()
        alert = make_price_alert()
        pa_repo.find_matching_alerts_for_product.return_value = [alert]

        nl_repo = MagicMock()
        nl_repo.exists_for_alert_and_product.return_value = False
        nl_repo.create.side_effect = lambda log: log

        user_repo = MagicMock()
        user_repo.get_by_id.return_value = make_user()

        sw_repo = MagicMock()
        sw_repo.get_by_id.return_value = make_source_website()

        email_svc = MagicMock()
        email_svc.send_price_alert_email.return_value = EmailResult(
            success=True, status_code=202
        )

        uc = self._build_use_case(
            product_repo=prod_repo,
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
            user_repo=user_repo,
            source_website_repo=sw_repo,
            email_service=email_svc,
        )
        sent, skipped, error = uc.execute(100)

        assert error is None
        assert len(sent) == 1
        assert sent[0].status == "sent"
        assert sent[0].product_id == 100
        assert sent[0].price_alert_id == 10
        assert sent[0].email_to == "user@example.com"
        assert skipped == 0

        # Email service called correctly
        email_svc.send_price_alert_email.assert_called_once_with(
            to_email="user@example.com",
            search_term="iPhone 13",
            product_title="iPhone 13 128GB Preto",
            product_price=2000.00,
            max_price=2500.00,
            product_url="https://example.com/product/1",
            source_website_name="Mercado Livre",
        )

        # last_triggered_at updated
        pa_repo.update.assert_called_once()

    def test_finds_matching_alerts_with_correct_params(self):
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = make_listing(
            title="Galaxy S24 Ultra", store_id=3, price=4500.00
        )

        pa_repo = MagicMock()
        pa_repo.find_matching_alerts_for_product.return_value = []

        uc = self._build_use_case(
            product_repo=prod_repo,
            price_alert_repo=pa_repo,
        )
        uc.execute(100)

        pa_repo.find_matching_alerts_for_product.assert_called_once_with(
            product_title="Galaxy S24 Ultra",
            source_website_id=3,
            current_price=4500.00,
        )

    # ------------------------------------------------------------------
    # Email failure
    # ------------------------------------------------------------------

    def test_records_failed_log_when_email_fails(self):
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = make_listing()

        pa_repo = MagicMock()
        pa_repo.find_matching_alerts_for_product.return_value = [make_price_alert()]

        nl_repo = MagicMock()
        nl_repo.exists_for_alert_and_product.return_value = False
        nl_repo.create.side_effect = lambda log: log

        user_repo = MagicMock()
        user_repo.get_by_id.return_value = make_user()

        sw_repo = MagicMock()
        sw_repo.get_by_id.return_value = make_source_website()

        email_svc = MagicMock()
        email_svc.send_price_alert_email.return_value = EmailResult(
            success=False, error_message="API key invalid"
        )

        uc = self._build_use_case(
            product_repo=prod_repo,
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
            user_repo=user_repo,
            source_website_repo=sw_repo,
            email_service=email_svc,
        )
        sent, skipped, error = uc.execute(100)

        # No sent logs (email failed) but error is None (processing completed)
        assert sent == []
        assert skipped == 0
        assert error is None

        # Log was still created with failed status
        nl_repo.create.assert_called_once()
        log_arg = nl_repo.create.call_args[0][0]
        assert log_arg.status == "failed"
        assert log_arg.error_message == "API key invalid"

        # last_triggered_at NOT updated (email failed)
        pa_repo.update.assert_not_called()

    # ------------------------------------------------------------------
    # User not found
    # ------------------------------------------------------------------

    def test_skips_alert_when_user_not_found(self):
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = make_listing()

        pa_repo = MagicMock()
        pa_repo.find_matching_alerts_for_product.return_value = [make_price_alert()]

        nl_repo = MagicMock()
        nl_repo.exists_for_alert_and_product.return_value = False

        user_repo = MagicMock()
        user_repo.get_by_id.return_value = None  # User not found

        sw_repo = MagicMock()
        sw_repo.get_by_id.return_value = make_source_website()

        uc = self._build_use_case(
            product_repo=prod_repo,
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
            user_repo=user_repo,
            source_website_repo=sw_repo,
        )
        sent, skipped, error = uc.execute(100)

        assert sent == []
        assert skipped == 1
        assert error is None

    # ------------------------------------------------------------------
    # Multiple alerts mixed
    # ------------------------------------------------------------------

    def test_handles_multiple_alerts_with_mixed_outcomes(self):
        """Test with 3 alerts: 1 already notified, 1 success, 1 email fail."""
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = make_listing()

        alert_dedup = make_price_alert(id=10, user_id=1)
        alert_success = make_price_alert(id=20, user_id=2)
        alert_fail = make_price_alert(id=30, user_id=3)

        pa_repo = MagicMock()
        pa_repo.find_matching_alerts_for_product.return_value = [
            alert_dedup,
            alert_success,
            alert_fail,
        ]

        nl_repo = MagicMock()
        # Alert 10: already notified; alerts 20, 30: not yet
        nl_repo.exists_for_alert_and_product.side_effect = lambda **kwargs: (
            kwargs["price_alert_id"] == 10
        )
        nl_repo.create.side_effect = lambda log: log

        user_repo = MagicMock()
        user_repo.get_by_id.side_effect = lambda uid: make_user(id=uid)

        sw_repo = MagicMock()
        sw_repo.get_by_id.return_value = make_source_website()

        email_svc = MagicMock()
        # Alert 20: success, Alert 30: failure
        call_count = {"n": 0}

        def email_side_effect(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return EmailResult(success=True, status_code=202)
            return EmailResult(success=False, error_message="quota exceeded")

        email_svc.send_price_alert_email.side_effect = email_side_effect

        uc = self._build_use_case(
            product_repo=prod_repo,
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
            user_repo=user_repo,
            source_website_repo=sw_repo,
            email_service=email_svc,
        )
        sent, skipped, error = uc.execute(100)

        assert error is None
        assert len(sent) == 1  # Only alert 20 succeeded
        assert sent[0].price_alert_id == 20
        assert skipped == 1  # Alert 10 was dedup-skipped
        assert email_svc.send_price_alert_email.call_count == 2

    # ------------------------------------------------------------------
    # Source website unknown
    # ------------------------------------------------------------------

    def test_uses_unknown_when_source_website_not_found(self):
        prod_repo = MagicMock()
        prod_repo.get_by_id.return_value = make_listing()

        pa_repo = MagicMock()
        pa_repo.find_matching_alerts_for_product.return_value = [make_price_alert()]

        nl_repo = MagicMock()
        nl_repo.exists_for_alert_and_product.return_value = False
        nl_repo.create.side_effect = lambda log: log

        user_repo = MagicMock()
        user_repo.get_by_id.return_value = make_user()

        sw_repo = MagicMock()
        sw_repo.get_by_id.return_value = None  # Not found

        email_svc = MagicMock()
        email_svc.send_price_alert_email.return_value = EmailResult(
            success=True, status_code=202
        )

        uc = self._build_use_case(
            product_repo=prod_repo,
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
            user_repo=user_repo,
            source_website_repo=sw_repo,
            email_service=email_svc,
        )
        sent, skipped, error = uc.execute(100)

        assert error is None
        assert len(sent) == 1
        call_kwargs = email_svc.send_price_alert_email.call_args[1]
        assert call_kwargs["source_website_name"] == "Unknown"
