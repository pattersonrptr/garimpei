from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProductCondition(str, Enum):
    """Product condition enumeration."""

    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"
    UNDETERMINED = "undetermined"


class Product(BaseModel):
    """Product domain entity representing a tracked product from e-commerce sites."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

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

    # Current price (calculated from price_history)
    current_price: float | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class PriceHistory(BaseModel):
    """PriceHistory domain entity representing a price record for a tracked product."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    product_id: int
    price: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
