"""What a plan allows (pure domain logic, no framework or database)."""

from dataclasses import dataclass

from src.app.billing.entities import Plan

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
