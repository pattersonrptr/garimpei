from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class ProductCondition(str, Enum):
    """Product condition enumeration."""

    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"
    UNDETERMINED = "undetermined"


@dataclass(kw_only=True)
class Product:
    """Product domain entity representing a tracked product from e-commerce sites."""

    # Identification
    id: int | None = None
    url: str
    title: str
    source_product_code: str | None = None

    # Content
    description: str | None = None
    image_urls: str | None = None  # URLs separated by commas

    # Location
    city: str | None = None
    state: str | None = None

    # Product details
    condition: ProductCondition = ProductCondition.UNDETERMINED
    seller_name: str | None = None
    is_available: bool = True

    # Source information
    source_website_id: int
    source_metadata: dict | None = None

    # The product this offer is for, once matched (see CanonicalProduct)
    canonical_product_id: int | None = None

    # Current price (calculated from price_history)
    current_price: float | None = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.condition = ProductCondition(self.condition)


@dataclass(frozen=True)
class ProductListFilters:
    """What a product listing is narrowed to (every field is optional).

    ``matching_user_id`` keeps only listings that one of that user's alerts
    found (``matching_alert_id``: that one alert): the alert's search term is in the title and the listing comes from
    one of the alert's sources. ``opportunities_only`` also requires the
    current price to be at or below that alert's max price.
    """

    title: str | None = None
    condition: str | None = None
    is_available: bool | None = None
    source_website_id: int | None = None
    matching_user_id: int | None = None
    matching_alert_id: int | None = None
    opportunities_only: bool = False


@dataclass(kw_only=True)
class PriceHistory:
    """PriceHistory domain entity representing a price record for a tracked product."""

    id: int | None = None
    product_id: int
    price: float
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ProductCategory(str, Enum):
    """What kind of thing a canonical product is. Books come first."""

    BOOK = "book"


class IdentifierKind(str, Enum):
    """The scheme of a product identifier."""

    ISBN13 = "isbn13"


@dataclass(kw_only=True)
class ProductIdentifier:
    """A code that identifies a canonical product (an ISBN-13, an EAN, ...)."""

    id: int | None = None
    kind: IdentifierKind
    value: str

    def __post_init__(self) -> None:
        self.kind = IdentifierKind(self.kind)


@dataclass(kw_only=True)
class CanonicalProduct:
    """The product itself, independent of any store.

    Offers (today's ``Product``) point to it. Category-specific data (author,
    publisher, ...) lives in ``attributes``, so a new category needs no new
    columns.
    """

    id: int | None = None
    category: ProductCategory
    title: str
    attributes: dict = field(default_factory=dict)
    identifiers: list[ProductIdentifier] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        self.category = ProductCategory(self.category)


@dataclass(frozen=True, kw_only=True)
class BookMetadata:
    """What a book metadata source knows about a book."""

    isbn13: str
    title: str
    subtitle: str | None = None
    authors: tuple[str, ...] = ()
    publisher: str | None = None
    year: int | None = None
    page_count: int | None = None
    synopsis: str | None = None
    cover_url: str | None = None


@dataclass(frozen=True, kw_only=True)
class QueuedProduct:
    """A product a collector should look up at a store, and when that store last
    gave it a price (None: never). Collectors check the stalest first."""

    kind: IdentifierKind
    value: str
    last_checked_at: datetime | None = None
