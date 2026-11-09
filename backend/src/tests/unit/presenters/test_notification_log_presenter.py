"""
Unit tests for NotificationLog Presenter.

Tests presentation layer (JSON:API formatting).
"""

from datetime import UTC, datetime

import pytest
from fastapi.responses import JSONResponse

from src.app.alerts.entities import NotificationLog as NotificationLogEntity
from src.app.alerts.http.notification_log_presenter import (
    NotificationLogPresenter,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_notification_log_entity():
    """Sample notification log entity for testing."""
    return NotificationLogEntity(
        id=1,
        price_alert_id=10,
        user_id=1,
        product_id=100,
        email_to="user@example.com",
        subject="🎯 Oportunidade! iPhone 13 por R$ 2,000.00 no Mercado Livre",
        status="sent",
        error_message=None,
        sent_at=datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC),
        created_at=datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC),
    )


@pytest.fixture
def sample_failed_notification_log():
    """Sample failed notification log entity for testing."""
    return NotificationLogEntity(
        id=2,
        price_alert_id=10,
        user_id=1,
        product_id=100,
        email_to="user@example.com",
        subject="🎯 Oportunidade! iPhone 13",
        status="failed",
        error_message="SendGrid API error: 401 Unauthorized",
        sent_at=datetime(2024, 6, 15, 11, 0, 0, tzinfo=UTC),
        created_at=datetime(2024, 6, 15, 11, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def sample_notification_log_collection(
    sample_notification_log_entity, sample_failed_notification_log
):
    return [sample_notification_log_entity, sample_failed_notification_log]


# ============================================================================
# handle_not_found
# ============================================================================


class TestHandleNotFound:
    def test_returns_json_response_with_404(self):
        result = NotificationLogPresenter.handle_not_found("id 999", "/data/id")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 404

    def test_includes_error_detail_with_identifier(self):
        result = NotificationLogPresenter.handle_not_found("id 42", "/data/id")

        body = result.body.decode()
        assert "42" in body
        assert "NOT_FOUND" in body


# ============================================================================
# handle_success
# ============================================================================


class TestHandleSuccess:
    def test_returns_single_resource_response(self, sample_notification_log_entity):
        result = NotificationLogPresenter.handle_success(sample_notification_log_entity)

        assert result.data.type == "notification_logs"
        assert result.data.id == "1"

    def test_includes_all_attributes(self, sample_notification_log_entity):
        result = NotificationLogPresenter.handle_success(sample_notification_log_entity)

        attrs = result.data.attributes
        assert attrs.price_alert_id == 10
        assert attrs.user_id == 1
        assert attrs.product_id == 100
        assert attrs.email_to == "user@example.com"
        assert attrs.status == "sent"
        assert attrs.error_message is None

    def test_handles_failed_status(self, sample_failed_notification_log):
        result = NotificationLogPresenter.handle_success(sample_failed_notification_log)

        attrs = result.data.attributes
        assert attrs.status == "failed"
        assert "Unauthorized" in attrs.error_message


# ============================================================================
# handle_collection_success
# ============================================================================


class TestHandleCollectionSuccess:
    def test_returns_collection_with_correct_count(
        self, sample_notification_log_collection
    ):
        result = NotificationLogPresenter.handle_collection_success(
            sample_notification_log_collection, 2
        )

        assert len(result.data) == 2
        assert result.meta["total"] == 2

    def test_each_item_has_correct_type(self, sample_notification_log_collection):
        result = NotificationLogPresenter.handle_collection_success(
            sample_notification_log_collection, 2
        )

        for item in result.data:
            assert item.type == "notification_logs"

    def test_empty_collection(self):
        result = NotificationLogPresenter.handle_collection_success([], 0)

        assert len(result.data) == 0
        assert result.meta["total"] == 0
