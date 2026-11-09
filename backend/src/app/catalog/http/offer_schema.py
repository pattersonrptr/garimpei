from pydantic import BaseModel, Field

from src.app.catalog.entities import ProductCondition
from src.common.jsonapi import ResourceObjectForCreation, SingleResourceRequest


class OfferAttributesForIngest(BaseModel):
    """One offer from a collector. Only price, link, condition, availability,
    store and seller city: the book's own data comes from its metadata."""

    isbn: str = Field(examples=["978-85-359-1484-9"])
    source_website_id: int
    url: str = Field(min_length=1)
    price: float = Field(gt=0, examples=[28.5])
    condition: ProductCondition = Field(examples=["used"])
    is_available: bool = True
    city: str | None = None
    state: str | None = None


class OfferResourceForIngest(ResourceObjectForCreation):
    type: str = Field(default="offers", examples=["offers"])
    attributes: OfferAttributesForIngest


class OfferIngestRequest(SingleResourceRequest):
    """Request schema for POST /offers."""

    data: OfferResourceForIngest
