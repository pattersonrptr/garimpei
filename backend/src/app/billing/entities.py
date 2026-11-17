from dataclasses import dataclass, field
from datetime import UTC, datetime


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(kw_only=True)
class Plan:
    """A subscription tier and the limits it grants."""

    id: int | None = None
    name: str  # "free", "pro", "business"
    display_name: str  # "Free", "Pro", "Business"
    price_cents: int = 0  # price in BRL cents (e.g. 2900 = R$29)
    max_active_alerts: int | None = None  # None = unlimited
    min_frequency_minutes: int = 360  # minimum check interval
    price_history_days: int | None = 7  # None = unlimited
    max_sources: int | None = None  # None = all
    has_push_notifications: bool = False
    has_whatsapp_notifications: bool = False
    has_api_access: bool = False
    is_active: bool = True


@dataclass(kw_only=True)
class Subscription:
    """A user's subscription to a plan."""

    id: int | None = None
    user_id: int
    plan_id: int
    status: str = "active"  # "active", "canceled", "past_due"
    current_period_start: datetime = field(default_factory=_now)
    current_period_end: datetime | None = None  # None = no expiry (free plan)
    canceled_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
