from datetime import datetime

from pydantic import BaseModel, Field

from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class PriceHistoryAttributes(BaseModel):
    """Price history attributes for responses."""

    product_id: int
    price: float
    created_at: datetime | None = None


class PriceHistoryAttributesForCreation(BaseModel):
    """Attributes for price history creation."""

    product_id: int
    price: float


class PriceHistoryResource(ResourceObject):
    """Price history resource following JSON:API specification."""

    type: str = Field(default="price_histories", examples=["price_histories"])
    attributes: PriceHistoryAttributes

    @classmethod
    def from_entity(cls, entity) -> "PriceHistoryResource":
        """Factory method: converts a PriceHistoryEntity to PriceHistoryResource."""
        return cls.from_model(
            entity,
            type_name="price_histories",
            attributes_field=PriceHistoryAttributes,
        )


class PriceHistoryResourceForCreation(ResourceObjectForCreation):
    """ResourceObject for price history creation (without id)."""

    type: str = Field(default="price_histories", examples=["price_histories"])
    attributes: PriceHistoryAttributesForCreation


class PriceHistoryCreateRequest(SingleResourceRequest):
    """Request schema for creating a price history record."""

    data: PriceHistoryResourceForCreation


class PriceHistoryReadResponse(SingleResourceResponse):
    """Response schema for a single price history record."""

    data: PriceHistoryResource


class PriceHistoriesCollectionResponse(CollectionResponse):
    """Response schema for a collection of price history records."""

    data: list[PriceHistoryResource]
