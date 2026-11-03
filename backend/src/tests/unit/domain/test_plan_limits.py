"""
Unit tests for plan limits domain logic.

Tests the PlanLimits checks exposed at the HTTP edge (JSON:API errors):
alert limit, frequency limit, source limit.
"""

from unittest.mock import MagicMock

from src.app.domain.plan_limits import FREE_PLAN_DEFAULTS, PlanLimits
from src.app.interfaces.http.plan_limits import (
    check_alert_limit,
    check_frequency_limit,
    check_source_limit,
)

# ============================================================================
# FREE_PLAN_DEFAULTS Tests
# ============================================================================


class TestFreePlanDefaults:
    """Tests for free plan default values."""

    def test_free_plan_defaults_should_have_correct_values(self):
        """
        Given: FREE_PLAN_DEFAULTS constant
        Then: Should have expected free tier limits
        """
        assert FREE_PLAN_DEFAULTS["max_active_alerts"] == 3
        assert FREE_PLAN_DEFAULTS["min_frequency_minutes"] == 360
        assert FREE_PLAN_DEFAULTS["price_history_days"] == 7
        assert FREE_PLAN_DEFAULTS["max_sources"] == 2


# ============================================================================
# check_alert_limit Tests
# ============================================================================


class TestCheckAlertLimit:
    """Tests for check_alert_limit()."""

    def _mock_db_with_alert_count(self, count: int) -> MagicMock:
        """Helper to create a mock db with a chained query returning count."""
        db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = count
        db.query.return_value = mock_query
        return db

    def test_unlimited_alerts_should_return_none(self):
        """
        Given: Plan with unlimited alerts (max_active_alerts=None)
        When: check_alert_limit is called
        Then: Should return None (no error)
        """
        limits = PlanLimits(
            plan_name="pro",
            max_active_alerts=None,
            min_frequency_minutes=30,
            price_history_days=90,
            max_sources=None,
        )
        db = MagicMock()

        result = check_alert_limit(db, 1, limits)
        assert result is None

    def test_under_limit_should_return_none(self):
        """
        Given: User with 2 active alerts and limit of 3
        When: check_alert_limit is called
        Then: Should return None (no error)
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )
        db = self._mock_db_with_alert_count(2)

        result = check_alert_limit(db, 1, limits)
        assert result is None

    def test_at_limit_should_return_error(self):
        """
        Given: User with 3 active alerts and limit of 3
        When: check_alert_limit is called
        Then: Should return a JsonApiError
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )
        db = self._mock_db_with_alert_count(3)

        result = check_alert_limit(db, 1, limits)
        assert result is not None
        assert result.code == "PLAN_LIMIT_REACHED"
        assert "3" in result.detail

    def test_over_limit_should_return_error(self):
        """
        Given: User with 5 active alerts and limit of 3
        When: check_alert_limit is called
        Then: Should return a JsonApiError
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )
        db = self._mock_db_with_alert_count(5)

        result = check_alert_limit(db, 1, limits)
        assert result is not None
        assert result.code == "PLAN_LIMIT_REACHED"


# ============================================================================
# check_frequency_limit Tests
# ============================================================================


class TestCheckFrequencyLimit:
    """Tests for check_frequency_limit()."""

    def test_frequency_above_minimum_should_return_none(self):
        """
        Given: Requested frequency is above plan minimum
        When: check_frequency_limit is called
        Then: Should return None (no error)
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )

        result = check_frequency_limit(360, limits)
        assert result is None

    def test_frequency_equal_to_minimum_should_return_none(self):
        """
        Given: Requested frequency equals plan minimum
        When: check_frequency_limit is called
        Then: Should return None (no error)
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )

        result = check_frequency_limit(360, limits)
        assert result is None

    def test_frequency_above_minimum_higher_should_return_none(self):
        """
        Given: Requested frequency 720 min with minimum 360 min
        When: check_frequency_limit is called
        Then: Should return None (higher is allowed)
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )

        result = check_frequency_limit(720, limits)
        assert result is None

    def test_frequency_below_minimum_should_return_error(self):
        """
        Given: Requested frequency 30 min with minimum 360 min
        When: check_frequency_limit is called
        Then: Should return a JsonApiError
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )

        result = check_frequency_limit(30, limits)
        assert result is not None
        assert result.code == "PLAN_LIMIT_REACHED"
        assert "360" in result.detail

    def test_pro_plan_allows_30_min_frequency(self):
        """
        Given: Pro plan with 30 min minimum frequency
        When: check_frequency_limit is called with 30
        Then: Should return None (allowed)
        """
        limits = PlanLimits(
            plan_name="pro",
            max_active_alerts=None,
            min_frequency_minutes=30,
            price_history_days=90,
            max_sources=None,
        )

        result = check_frequency_limit(30, limits)
        assert result is None


# ============================================================================
# check_source_limit Tests
# ============================================================================


class TestCheckSourceLimit:
    """Tests for check_source_limit()."""

    def test_unlimited_sources_should_return_none(self):
        """
        Given: Plan with unlimited sources (max_sources=None)
        When: check_source_limit is called
        Then: Should return None (no error)
        """
        limits = PlanLimits(
            plan_name="pro",
            max_active_alerts=None,
            min_frequency_minutes=30,
            price_history_days=90,
            max_sources=None,
        )

        result = check_source_limit(10, limits)
        assert result is None

    def test_under_source_limit_should_return_none(self):
        """
        Given: 1 source requested with limit of 2
        When: check_source_limit is called
        Then: Should return None (no error)
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )

        result = check_source_limit(1, limits)
        assert result is None

    def test_at_source_limit_should_return_none(self):
        """
        Given: 2 sources requested with limit of 2
        When: check_source_limit is called
        Then: Should return None (exactly at limit is OK)
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )

        result = check_source_limit(2, limits)
        assert result is None

    def test_over_source_limit_should_return_error(self):
        """
        Given: 3 sources requested with limit of 2
        When: check_source_limit is called
        Then: Should return a JsonApiError
        """
        limits = PlanLimits(
            plan_name="free",
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
        )

        result = check_source_limit(3, limits)
        assert result is not None
        assert result.code == "PLAN_LIMIT_REACHED"
        assert "2" in result.detail
