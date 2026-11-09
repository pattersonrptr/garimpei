from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


@dataclass(kw_only=True)
class PriceAlert:
    """PriceAlert domain entity representing a user's price monitoring alert."""

    id: int | None = None
    search_term: str
    max_price: float
    is_active: bool = True
    frequency_minutes: int = 60
    last_triggered_at: datetime | None = None
    user_id: int | None = None
    search_config_id: int | None = None
    source_website_ids: list[int] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None


NotificationStatus = Literal["sent", "failed"]


@dataclass(kw_only=True)
class NotificationLog:
    """NotificationLog domain entity representing a sent email notification."""

    id: int | None = None
    price_alert_id: int
    user_id: int
    product_id: int | None = None
    email_to: str
    subject: str
    status: NotificationStatus = "sent"
    error_message: str | None = None
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
