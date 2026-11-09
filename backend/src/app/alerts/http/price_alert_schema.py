from datetime import datetime

from pydantic import BaseModel, Field

from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class PriceAlertAttributes(BaseModel):
    """Price alert attributes for responses."""

    search_term: str
    max_price: float
    is_active: bool
    frequency_minutes: int
    last_triggered_at: datetime | None = None
    user_id: int | None = None
    search_config_id: int | None = None
    source_website_ids: list[int] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PriceAlertAttributesForCreation(BaseModel):
    """Attributes for price alert creation."""

    search_term: str
    max_price: float
    user_id: int
    is_active: bool = True
    frequency_minutes: int = 60
    source_website_ids: list[int] = Field(default_factory=list)


class PriceAlertAttributesForUpdate(BaseModel):
    """Attributes for price alert update — all optional."""

    search_term: str | None = None
    max_price: float | None = None
    is_active: bool | None = None
    frequency_minutes: int | None = None
    source_website_ids: list[int] | None = None


class PriceAlertResource(ResourceObject):
    """Price alert resource following JSON:API specification."""

    type: str = Field(default="price_alerts", examples=["price_alerts"])
    attributes: PriceAlertAttributes

    @classmethod
    def from_entity(cls, entity) -> "PriceAlertResource":
        """Factory method: converts a PriceAlertEntity to PriceAlertResource."""
        return cls.from_model(
            entity,
            type_name="price_alerts",
            attributes_field=PriceAlertAttributes,
        )


class PriceAlertResourceForCreation(ResourceObjectForCreation):
    """ResourceObject for price alert creation (without id)."""

    type: str = Field(default="price_alert", examples=["price_alert"])
    attributes: PriceAlertAttributesForCreation


class PriceAlertResourceForUpdate(ResourceObjectForCreation):
    """ResourceObject for price alert update (without id)."""

    type: str = Field(default="price_alert", examples=["price_alert"])
    attributes: PriceAlertAttributesForUpdate


class PriceAlertCreateRequest(SingleResourceRequest):
    """Request schema for creating a price alert."""

    data: PriceAlertResourceForCreation


class PriceAlertUpdateRequest(SingleResourceRequest):
    """Request schema for updating a price alert."""

    data: PriceAlertResourceForUpdate


class PriceAlertReadResponse(SingleResourceResponse):
    """Response schema for a single price alert."""

    data: PriceAlertResource


class PriceAlertsCollectionResponse(CollectionResponse):
    """Response schema for a collection of price alerts."""

    data: list[PriceAlertResource]
