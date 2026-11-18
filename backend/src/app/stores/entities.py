from dataclasses import dataclass, field
from datetime import UTC, datetime


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(kw_only=True)
class Store:
    """A store whose offers are collected (an e-commerce site or marketplace)."""

    id: int | None = None
    name: str
    base_url: str
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
