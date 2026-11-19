"""Unit tests for the pure Run Now limit rules (no FastAPI, no database).

Moved from tests/unit/domain/test_plan_limit_rules.py with the rules.
"""

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.app.searches import entities
from src.app.searches.entities import (
    RunLimits,
    manual_run_violation,
    source_limit_violation,
)

FREE = RunLimits(plan_name="free", min_frequency_minutes=360, max_sources=2)
PRO = RunLimits(plan_name="pro", min_frequency_minutes=30, max_sources=None)
NOW = datetime(2026, 11, 3, 20, 0, tzinfo=UTC)


def test_domain_module_has_no_framework_or_database_imports():
    tree = ast.parse(Path(entities.__file__).read_text(encoding="utf-8"))
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
    source = Path(entities.__file__).read_text(encoding="utf-8")
    assert "infrastructure" not in source


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
