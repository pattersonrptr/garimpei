"""Plan limit rules (pure domain logic).

No framework or database here: callers load the data (limits, counts,
timestamps) and these functions decide whether an operation is allowed.
What a plan allows (PlanLimits) lives in src/app/billing/limits.py; the
FastAPI dependency and the JSON:API error mapping live in
src/app/interfaces/http/plan_limits.py.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.app.billing.limits import PlanLimits


@dataclass(frozen=True)
class PlanLimitViolation:
    """Why an operation exceeds the user's plan (mapped to an API error)."""

    title: str
    detail: str
    pointer: str | None = None
    # Machine-readable facts so clients can explain it in the user's language:
    # {"limit": "<name>", "value": <number>, "plan": "<plan name>"}
    meta: dict | None = None


def alert_limit_violation(
    active_alert_count: int, limits: PlanLimits
) -> PlanLimitViolation | None:
    """Can the user create one more active alert?"""
    if limits.max_active_alerts is None:
        return None  # unlimited
    if active_alert_count >= limits.max_active_alerts:
        return PlanLimitViolation(
            title="Alert limit reached",
            detail=(
                f"Your {limits.plan_name} plan allows up to "
                f"{limits.max_active_alerts} active alerts. "
                f"Upgrade your plan for more."
            ),
            pointer="/data/attributes/is_active",
            meta={
                "limit": "max_active_alerts",
                "value": limits.max_active_alerts,
                "plan": limits.plan_name,
            },
        )
    return None


def frequency_limit_violation(
    frequency_minutes: int, limits: PlanLimits
) -> PlanLimitViolation | None:
    """Is the requested check frequency allowed by the plan?"""
    if frequency_minutes < limits.min_frequency_minutes:
        return PlanLimitViolation(
            title="Frequency too high for your plan",
            detail=(
                f"Your {limits.plan_name} plan allows minimum frequency of "
                f"{limits.min_frequency_minutes} minutes. "
                f"Upgrade your plan for faster checks."
            ),
            pointer="/data/attributes/frequency_minutes",
            meta={
                "limit": "min_frequency_minutes",
                "value": limits.min_frequency_minutes,
                "plan": limits.plan_name,
            },
        )
    return None


def source_limit_violation(
    source_count: int, limits: PlanLimits
) -> PlanLimitViolation | None:
    """Is the number of sources per alert allowed by the plan?"""
    if limits.max_sources is None:
        return None  # unlimited
    if source_count > limits.max_sources:
        return PlanLimitViolation(
            title="Source limit reached",
            detail=(
                f"Your {limits.plan_name} plan allows up to "
                f"{limits.max_sources} sources per alert. "
                f"Upgrade your plan for more."
            ),
            pointer="/data/attributes/source_website_ids",
            meta={
                "limit": "max_sources",
                "value": limits.max_sources,
                "plan": limits.plan_name,
            },
        )
    return None


def manual_run_violation(
    last_run_started_at: datetime | None, now: datetime, limits: PlanLimits
) -> PlanLimitViolation | None:
    """
    A manual "Run Now" must respect the plan's minimum check interval,
    otherwise it would be a way around min_frequency_minutes.
    """
    if last_run_started_at is None:
        return None
    if last_run_started_at.tzinfo is None:  # stored as naive UTC
        last_run_started_at = last_run_started_at.replace(tzinfo=UTC)
    next_allowed = last_run_started_at + timedelta(minutes=limits.min_frequency_minutes)
    if now < next_allowed:
        wait_minutes = int((next_allowed - now).total_seconds() // 60) + 1
        return PlanLimitViolation(
            title="Search ran recently",
            detail=(
                f"Your {limits.plan_name} plan allows one check every "
                f"{limits.min_frequency_minutes} minutes. "
                f"Try again in {wait_minutes} minutes."
            ),
            meta={
                "limit": "manual_run_interval",
                "value": limits.min_frequency_minutes,
                "wait_minutes": wait_minutes,
                "plan": limits.plan_name,
            },
        )
    return None
