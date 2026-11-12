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


@dataclass(frozen=True, kw_only=True)
class OfferPrice:
    """Today's lowest price in stock for a condition, and where."""

    price: float
    store: str  # the store's slug, e.g. "estante_virtual"


@dataclass(frozen=True, kw_only=True)
class ProductSnapshot:
    """What "my alerts" shows about the product an alert watches.

    ``lowest`` and ``verdicts`` are keyed by condition ("new", "used").
    """

    id: int
    category: str
    title: str
    isbn13: str | None = None
    cover_url: str | None = None
    lowest: dict[str, OfferPrice] = field(default_factory=dict)
    verdicts: dict[str, str] = field(default_factory=dict)

    def lowest_for(self, condition: str | None) -> tuple[str, OfferPrice] | None:
        """The cheapest offer the alert wants: (its condition, price and store)."""
        wanted = ("new", "used") if (condition or "any") == "any" else (condition,)
        found = [(c, self.lowest[c]) for c in wanted if c in self.lowest]
        return min(found, key=lambda item: item[1].price, default=None)


@dataclass(frozen=True, kw_only=True)
class Store:
    """A store an alert can watch and an e-mail names."""

    id: int
    name: str


@dataclass(frozen=True, kw_only=True)
class AlertOwner:
    """The user who owns an alert, as far as alerts needs: where to write."""

    id: int
    email: str


@dataclass(frozen=True, kw_only=True)
class SentNotice:
    """One e-mail sent for an alert: when, and which store's offer."""

    sent_at: datetime
    store: str | None


@dataclass(frozen=True, kw_only=True)
class NoticeHistory:
    recent: tuple[SentNotice, ...] = ()  # newest first
    total: int = 0


@dataclass(frozen=True, kw_only=True)
class MyAlert:
    """One line of "my alerts": the alert, its product today, and the e-mails sent."""

    alert: PriceAlert
    product: ProductSnapshot | None
    notices: NoticeHistory


@dataclass(frozen=True, kw_only=True)
class MailResult:
    """Whether an alert e-mail went out; the reason when it did not."""

    success: bool
    error_message: str | None = None


@dataclass(kw_only=True)
class KeywordSearch:
    """The collector search a keyword alert keeps running (a SearchConfig).

    One per term and user, shared by that user's alerts on the term; it is
    paused when no active alert uses it any more.
    """

    id: int | None = None
    search_term: str
    is_active: bool = True
    frequency_days: int = 1
    user_id: int | None = None
    source_website_ids: list[int] = field(default_factory=list)
