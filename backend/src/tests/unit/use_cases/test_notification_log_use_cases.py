"""
Unit tests for NotificationLog use cases.

Tests CRUD use cases and SendPriceAlertNotificationUseCase with mocked repos + email service.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from src.app.entities.notification_log import NotificationLog as NotificationLogEntity
from src.app.entities.price_alert import PriceAlert as PriceAlertEntity
from src.app.entities.product import Product as ProductEntity
from src.app.entities.source_website import SourceWebsite as SourceWebsiteEntity
from src.app.entities.user import User as UserEntity
from src.app.interfaces.services.email_service import EmailResult
from src.app.use_cases.notification_log_use_cases import (
    CreateNotificationLogUseCase,
    DeleteNotificationLogUseCase,
    GetNotificationLogByIdUseCase,
    GetNotificationLogsByPriceAlertIdUseCase,
    ListNotificationLogsUseCase,
    SendPriceAlertNotificationUseCase,
)

# ============================================================================
# Helpers
# ============================================================================


def make_notification_log(**overrides):
    defaults = {
        "id": 1,
        "price_alert_id": 10,
        "user_id": 1,
        "product_id": 100,
        "email_to": "user@example.com",
        "subject": "🎯 Oportunidade! iPhone 13",
        "status": "sent",
        "error_message": None,
        "sent_at": datetime(2024, 1, 1, tzinfo=UTC),
        "created_at": datetime(2024, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return NotificationLogEntity(**defaults)


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


def make_product(**overrides):
    defaults = {
        "id": 100,
        "url": "https://example.com/product/1",
        "title": "iPhone 13 128GB",
        "source_website_id": 1,
        "current_price": 2000.00,
        "is_available": True,
        "created_at": datetime(2024, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2024, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return ProductEntity(**defaults)


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
# CRUD Use Cases
# ============================================================================


class TestCreateNotificationLogUseCase:
    def test_execute_creates_and_returns_entity(self):
        repo = MagicMock()
        log = make_notification_log(id=None)
        created = make_notification_log(id=1)
        repo.create.return_value = created

        result = CreateNotificationLogUseCase(repo).execute(log)

        repo.create.assert_called_once_with(log)
        assert result.id == 1

    def test_execute_returns_entity_with_generated_id(self):
        repo = MagicMock()
        log = make_notification_log(id=None)
        repo.create.return_value = make_notification_log(id=42)

        result = CreateNotificationLogUseCase(repo).execute(log)
        assert result.id == 42


class TestGetNotificationLogByIdUseCase:
    def test_execute_returns_entity_when_found(self):
        repo = MagicMock()
        repo.get_by_id.return_value = make_notification_log(id=1)

        result = GetNotificationLogByIdUseCase(repo).execute(1)

        assert result is not None
        assert result.id == 1

    def test_execute_returns_none_when_not_found(self):
        repo = MagicMock()
        repo.get_by_id.return_value = None

        result = GetNotificationLogByIdUseCase(repo).execute(999)
        assert result is None


class TestGetNotificationLogsByPriceAlertIdUseCase:
    def test_execute_returns_list_of_entities(self):
        repo = MagicMock()
        logs = [make_notification_log(id=1), make_notification_log(id=2)]
        repo.get_by_price_alert_id.return_value = logs

        result = GetNotificationLogsByPriceAlertIdUseCase(repo).execute(10)

        assert len(result) == 2
        repo.get_by_price_alert_id.assert_called_once_with(10)

    def test_execute_returns_empty_list_when_no_logs(self):
        repo = MagicMock()
        repo.get_by_price_alert_id.return_value = []

        result = GetNotificationLogsByPriceAlertIdUseCase(repo).execute(999)
        assert result == []


class TestListNotificationLogsUseCase:
    def test_execute_returns_paginated_results(self):
        repo = MagicMock()
        logs = [make_notification_log(id=1)]
        repo.get_all.return_value = (logs, 1)

        result_logs, total = ListNotificationLogsUseCase(repo).execute(
            limit=10, offset=0
        )

        assert len(result_logs) == 1
        assert total == 1

    def test_execute_passes_pagination_params(self):
        repo = MagicMock()
        repo.get_all.return_value = ([], 0)

        ListNotificationLogsUseCase(repo).execute(
            limit=5, offset=10, sort_by="sent_at", sort_order="asc"
        )

        repo.get_all.assert_called_once_with(
            limit=5, offset=10, sort_by="sent_at", sort_order="asc"
        )


class TestDeleteNotificationLogUseCase:
    def test_execute_returns_true_when_deleted(self):
        repo = MagicMock()
        repo.delete.return_value = True

        result = DeleteNotificationLogUseCase(repo).execute(1)
        assert result is True

    def test_execute_returns_false_when_not_found(self):
        repo = MagicMock()
        repo.delete.return_value = False

        result = DeleteNotificationLogUseCase(repo).execute(999)
        assert result is False


# ============================================================================
# SendPriceAlertNotificationUseCase
# ============================================================================


class TestSendPriceAlertNotificationUseCase:
    def _build_use_case(
        self,
        price_alert_repo=None,
        product_repo=None,
        user_repo=None,
        source_website_repo=None,
        notification_log_repo=None,
        email_service=None,
    ):
        return SendPriceAlertNotificationUseCase(
            price_alert_repo=price_alert_repo or MagicMock(),
            product_repo=product_repo or MagicMock(),
            user_repo=user_repo or MagicMock(),
            source_website_repo=source_website_repo or MagicMock(),
            notification_log_repo=notification_log_repo or MagicMock(),
            email_service=email_service or MagicMock(),
        )

    def test_returns_error_when_alert_not_found(self):
        pa_repo = MagicMock()
        pa_repo.get_by_id.return_value = None

        uc = self._build_use_case(price_alert_repo=pa_repo)
        logs, error = uc.execute(999)

        assert logs == []
        assert error == "Price alert not found"

    def test_returns_error_when_alert_inactive(self):
        pa_repo = MagicMock()
        pa_repo.get_by_id.return_value = make_price_alert(is_active=False)

        uc = self._build_use_case(price_alert_repo=pa_repo)
        logs, error = uc.execute(10)

        assert logs == []
        assert "inactive" in error

    @patch("src.app.use_cases.notification_log_use_cases.settings")
    def test_returns_error_when_rate_limited(self, mock_settings):
        mock_settings.NOTIFICATION_RATE_LIMIT_MINUTES = 60
        pa_repo = MagicMock()
        pa_repo.get_by_id.return_value = make_price_alert()

        nl_repo = MagicMock()
        nl_repo.count_since.return_value = 1  # Already sent within window

        uc = self._build_use_case(
            price_alert_repo=pa_repo, notification_log_repo=nl_repo
        )
        logs, error = uc.execute(10)

        assert logs == []
        assert "Rate limited" in error

    @patch("src.app.use_cases.notification_log_use_cases.settings")
    def test_returns_error_when_no_matching_products(self, mock_settings):
        mock_settings.NOTIFICATION_RATE_LIMIT_MINUTES = 60
        pa_repo = MagicMock()
        pa_repo.get_by_id.return_value = make_price_alert()

        nl_repo = MagicMock()
        nl_repo.count_since.return_value = 0

        prod_repo = MagicMock()
        prod_repo.search_by_term_and_sources.return_value = ([], 0)

        uc = self._build_use_case(
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
            product_repo=prod_repo,
        )
        logs, error = uc.execute(10)

        assert logs == []
        assert "No matching products" in error

    @patch("src.app.use_cases.notification_log_use_cases.settings")
    def test_returns_error_when_user_not_found(self, mock_settings):
        mock_settings.NOTIFICATION_RATE_LIMIT_MINUTES = 60
        pa_repo = MagicMock()
        pa_repo.get_by_id.return_value = make_price_alert()

        nl_repo = MagicMock()
        nl_repo.count_since.return_value = 0

        prod_repo = MagicMock()
        prod_repo.search_by_term_and_sources.return_value = (
            [make_product()],
            1,
        )

        user_repo = MagicMock()
        user_repo.get_by_id.return_value = None

        uc = self._build_use_case(
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
            product_repo=prod_repo,
            user_repo=user_repo,
        )
        logs, error = uc.execute(10)

        assert logs == []
        assert "User not found" in error

    @patch("src.app.use_cases.notification_log_use_cases.settings")
    def test_sends_email_and_creates_log_on_success(self, mock_settings):
        mock_settings.NOTIFICATION_RATE_LIMIT_MINUTES = 60
        pa_repo = MagicMock()
        alert = make_price_alert()
        pa_repo.get_by_id.return_value = alert

        nl_repo = MagicMock()
        nl_repo.count_since.return_value = 0
        nl_repo.create.side_effect = lambda log: log

        prod_repo = MagicMock()
        product = make_product(current_price=2000.00)
        prod_repo.search_by_term_and_sources.return_value = ([product], 1)

        user_repo = MagicMock()
        user_repo.get_by_id.return_value = make_user()

        sw_repo = MagicMock()
        sw_repo.get_by_id.return_value = make_source_website()

        email_svc = MagicMock()
        email_svc.send_price_alert_email.return_value = EmailResult(
            success=True, status_code=202
        )

        uc = self._build_use_case(
            price_alert_repo=pa_repo,
            product_repo=prod_repo,
            user_repo=user_repo,
            source_website_repo=sw_repo,
            notification_log_repo=nl_repo,
            email_service=email_svc,
        )
        logs, error = uc.execute(10)

        assert error is None
        assert len(logs) == 1
        assert logs[0].status == "sent"
        assert logs[0].email_to == "user@example.com"
        assert logs[0].product_id == 100

        # Email service called with correct params
        email_svc.send_price_alert_email.assert_called_once_with(
            to_email="user@example.com",
            search_term="iPhone 13",
            product_title="iPhone 13 128GB",
            product_price=2000.00,
            max_price=2500.00,
            product_url="https://example.com/product/1",
            source_website_name="Mercado Livre",
        )

        # last_triggered_at updated
        pa_repo.update.assert_called_once()

    @patch("src.app.use_cases.notification_log_use_cases.settings")
    def test_records_failed_log_when_email_fails(self, mock_settings):
        mock_settings.NOTIFICATION_RATE_LIMIT_MINUTES = 60
        pa_repo = MagicMock()
        pa_repo.get_by_id.return_value = make_price_alert()

        nl_repo = MagicMock()
        nl_repo.count_since.return_value = 0
        nl_repo.create.side_effect = lambda log: log

        prod_repo = MagicMock()
        prod_repo.search_by_term_and_sources.return_value = (
            [make_product()],
            1,
        )

        user_repo = MagicMock()
        user_repo.get_by_id.return_value = make_user()

        sw_repo = MagicMock()
        sw_repo.get_by_id.return_value = make_source_website()

        email_svc = MagicMock()
        email_svc.send_price_alert_email.return_value = EmailResult(
            success=False, error_message="API key invalid"
        )

        uc = self._build_use_case(
            price_alert_repo=pa_repo,
            product_repo=prod_repo,
            user_repo=user_repo,
            source_website_repo=sw_repo,
            notification_log_repo=nl_repo,
            email_service=email_svc,
        )
        logs, error = uc.execute(10)

        assert len(logs) == 1
        assert logs[0].status == "failed"
        assert logs[0].error_message == "API key invalid"
        assert "Email send failed" in error

    @patch("src.app.use_cases.notification_log_use_cases.settings")
    def test_searches_products_with_correct_params(self, mock_settings):
        mock_settings.NOTIFICATION_RATE_LIMIT_MINUTES = 60
        pa_repo = MagicMock()
        alert = make_price_alert(
            search_term="Galaxy S24",
            max_price=3000.00,
            source_website_ids=[1, 3],
        )
        pa_repo.get_by_id.return_value = alert

        nl_repo = MagicMock()
        nl_repo.count_since.return_value = 0

        prod_repo = MagicMock()
        prod_repo.search_by_term_and_sources.return_value = ([], 0)

        uc = self._build_use_case(
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
            product_repo=prod_repo,
        )
        uc.execute(10)

        prod_repo.search_by_term_and_sources.assert_called_once_with(
            search_term="Galaxy S24",
            source_website_ids=[1, 3],
            max_price=3000.00,
            limit=1,
            offset=0,
        )

    @patch("src.app.use_cases.notification_log_use_cases.settings")
    def test_uses_unknown_when_source_website_not_found(self, mock_settings):
        mock_settings.NOTIFICATION_RATE_LIMIT_MINUTES = 60
        pa_repo = MagicMock()
        pa_repo.get_by_id.return_value = make_price_alert()

        nl_repo = MagicMock()
        nl_repo.count_since.return_value = 0
        nl_repo.create.side_effect = lambda log: log

        prod_repo = MagicMock()
        prod_repo.search_by_term_and_sources.return_value = (
            [make_product()],
            1,
        )

        user_repo = MagicMock()
        user_repo.get_by_id.return_value = make_user()

        sw_repo = MagicMock()
        sw_repo.get_by_id.return_value = None  # Source website not found

        email_svc = MagicMock()
        email_svc.send_price_alert_email.return_value = EmailResult(
            success=True, status_code=202
        )

        uc = self._build_use_case(
            price_alert_repo=pa_repo,
            product_repo=prod_repo,
            user_repo=user_repo,
            source_website_repo=sw_repo,
            notification_log_repo=nl_repo,
            email_service=email_svc,
        )
        logs, error = uc.execute(10)

        # Should use "Unknown" as website name
        email_svc.send_price_alert_email.assert_called_once()
        call_kwargs = email_svc.send_price_alert_email.call_args
        assert call_kwargs[1]["source_website_name"] == "Unknown"

    @patch("src.app.use_cases.notification_log_use_cases.settings")
    def test_rate_limit_checks_correct_time_window(self, mock_settings):
        mock_settings.NOTIFICATION_RATE_LIMIT_MINUTES = 120  # 2 hours

        pa_repo = MagicMock()
        pa_repo.get_by_id.return_value = make_price_alert()

        nl_repo = MagicMock()
        nl_repo.count_since.return_value = 1

        uc = self._build_use_case(
            price_alert_repo=pa_repo,
            notification_log_repo=nl_repo,
        )
        logs, error = uc.execute(10)

        # Should check with 120-minute window
        nl_repo.count_since.assert_called_once()
        call_args = nl_repo.count_since.call_args
        assert call_args[0][0] == 10  # price_alert_id
        # The since datetime should be ~120 minutes ago
        since_arg = call_args[0][1]
        assert isinstance(since_arg, datetime)
        assert "120 minutes" in error
