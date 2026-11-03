"""Unit tests for the pure plan-limit rules (no FastAPI, no database)."""

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.app.domain import plan_limits
from src.app.domain.plan_limits import (
    PlanLimits,
    alert_limit_violation,
    frequency_limit_violation,
    limits_for_plan,
    manual_run_violation,
    source_limit_violation,
)
from src.app.entities.plan import Plan

FREE = limits_for_plan(None)
PRO = PlanLimits(
    plan_name="pro",
    max_active_alerts=None,
    min_frequency_minutes=30,
    price_history_days=None,
    max_sources=None,
)
NOW = datetime(2026, 11, 3, 20, 0, tzinfo=UTC)


def test_domain_module_has_no_framework_or_database_imports():
    tree = ast.parse(Path(plan_limits.__file__).read_text(encoding="utf-8"))
    imported = {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported & {"fastapi", "sqlalchemy", "sendgrid"}
    source = Path(plan_limits.__file__).read_text(encoding="utf-8")
    assert "infrastructure" not in source


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


@pytest.mark.parametrize(
    "count,blocked", [(0, False), (2, False), (3, True), (5, True)]
)
def test_alert_limit(count, blocked):
    violation = alert_limit_violation(count, FREE)
    assert (violation is not None) is blocked
    assert alert_limit_violation(100, PRO) is None


@pytest.mark.parametrize("minutes,blocked", [(359, True), (360, False), (1440, False)])
def test_frequency_limit(minutes, blocked):
    assert (frequency_limit_violation(minutes, FREE) is not None) is blocked


@pytest.mark.parametrize("sources,blocked", [(1, False), (2, False), (3, True)])
def test_source_limit(sources, blocked):
    assert (source_limit_violation(sources, FREE) is not None) is blocked
    assert source_limit_violation(10, PRO) is None


class TestManualRun:
    def test_first_run_is_allowed(self):
        assert manual_run_violation(None, NOW, FREE) is None

    def test_blocked_inside_the_plan_interval(self):
        violation = manual_run_violation(NOW - timedelta(minutes=100), NOW, FREE)
        assert violation is not None
        assert "360 minutes" in violation.detail
        assert "261 minutes" in violation.detail

    def test_allowed_after_the_interval(self):
        assert manual_run_violation(NOW - timedelta(minutes=360), NOW, FREE) is None

    def test_naive_timestamps_are_treated_as_utc(self):
        naive = (NOW - timedelta(minutes=40)).replace(tzinfo=None)
        assert manual_run_violation(naive, NOW, FREE) is not None  # 360 min
        assert manual_run_violation(naive, NOW, PRO) is None  # 30 min
