"""Unit tests for billing's limits_for_plan (moved from
tests/unit/domain/test_plan_limit_rules.py when the Run Now rules moved to
saved searches)."""

from src.app.billing.entities import Plan
from src.app.billing.limits import limits_for_plan

FREE = limits_for_plan(None)


class TestLimitsForPlan:
    def test_no_plan_means_free_defaults(self):
        assert FREE.plan_name == "free"
        assert FREE.max_active_alerts == 3
        assert FREE.min_frequency_minutes == 360
        assert FREE.max_sources == 2

    def test_copies_plan_limits(self):
        plan = Plan(
            name="pro",
            display_name="Pro",
            max_active_alerts=20,
            min_frequency_minutes=60,
            price_history_days=None,
            max_sources=None,
        )
        limits = limits_for_plan(plan)
        assert (limits.plan_name, limits.max_active_alerts) == ("pro", 20)
        assert limits.min_frequency_minutes == 60
        assert limits.max_sources is None
