"""Plan limit rules (pure domain logic).

No framework or database here: callers load the data (plan, counts,
timestamps) and these functions decide whether an operation is allowed.
The FastAPI dependency and the JSON:API error mapping live in
src/app/interfaces/http/plan_limits.py.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.app.entities.plan import Plan

# Default limits for users without a subscription (free tier)
FREE_PLAN_DEFAULTS = {
    "max_active_alerts": 3,
    "min_frequency_minutes": 360,
    "price_history_days": 7,
    "max_sources": 2,
}


@dataclass
class PlanLimits:
    plan_name: str
    max_active_alerts: int | None  # None = unlimited
    min_frequency_minutes: int
    price_history_days: int | None  # None = unlimited
    max_sources: int | None  # None = all


@dataclass(frozen=True)
class PlanLimitViolation:
    """Why an operation exceeds the user's plan (mapped to an API error)."""

    title: str
    detail: str
    pointer: str | None = None


def limits_for_plan(plan: Plan | None) -> PlanLimits:
    """Limits of the user's plan, or the free defaults if there is none."""
    if plan is None:
        return PlanLimits(
            plan_name="free",
            max_active_alerts=FREE_PLAN_DEFAULTS["max_active_alerts"],
            min_frequency_minutes=FREE_PLAN_DEFAULTS["min_frequency_minutes"],
            price_history_days=FREE_PLAN_DEFAULTS["price_history_days"],
            max_sources=FREE_PLAN_DEFAULTS["max_sources"],
        )
    return PlanLimits(
        plan_name=plan.name,
        max_active_alerts=plan.max_active_alerts,
        min_frequency_minutes=plan.min_frequency_minutes,
        price_history_days=plan.price_history_days,
        max_sources=plan.max_sources,
    )


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
        )
    return None
