from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

# What a book alert watches: new copies, used copies, or either.
BookCondition = Literal["new", "used", "any"]
BOOK_CONDITIONS: tuple[str, ...] = ("new", "used", "any")


@dataclass(kw_only=True)
class PriceAlert:
    """PriceAlert domain entity representing a user's price monitoring alert.

    Two kinds: a keyword alert (``search_term`` in a listing's title, on the
    chosen stores) and a book alert (``canonical_product_id`` set: any store's
    offer for that book, in ``condition``, at or under ``max_price``). A book
    alert keeps the book's title in ``search_term`` for display.
    """

    id: int | None = None
    search_term: str
    max_price: float
    is_active: bool = True
    frequency_minutes: int = 60
    last_triggered_at: datetime | None = None
    user_id: int | None = None
    search_config_id: int | None = None
    source_website_ids: list[int] = field(default_factory=list)
    canonical_product_id: int | None = None
    condition: BookCondition | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None

    @property
    def is_book_alert(self) -> bool:
        return self.canonical_product_id is not None

    def accepts_condition(self, condition: str) -> bool:
        """Whether an offer in ``condition`` ("new", "used"...) is wanted."""
        wanted = self.condition or "any"
        if wanted == "any":
            return condition in ("new", "used")
        return condition == wanted


@dataclass(frozen=True, kw_only=True)
class BookRef:
    """The book a book alert points at, as the alerts module needs it."""

    id: int
    isbn13: str
    title: str


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
