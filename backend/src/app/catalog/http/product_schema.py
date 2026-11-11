from datetime import datetime

from pydantic import BaseModel, Field

from src.app.catalog.entities import ProductCondition
from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class ProductAttributes(BaseModel):
    """Product attributes for responses."""

    url: str
    title: str
    source_product_code: str | None = None
    description: str | None = None
    image_urls: str | None = None
    city: str | None = None
    state: str | None = None
    condition: ProductCondition = ProductCondition.UNDETERMINED
    seller_name: str | None = None
    is_available: bool = True
    source_website_id: int
    source_metadata: dict | None = None
    canonical_product_id: int | None = None
    current_price: float | None = None
    last_checked_at: datetime | None = Field(
        default=None,
        description="When a collector last saw this offer (its latest price point)",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductAttributesForCreation(BaseModel):
    """Attributes for product creation."""

    url: str
    title: str
    source_product_code: str | None = None
    description: str | None = None
    image_urls: str | None = None
    city: str | None = None
    state: str | None = None
    condition: ProductCondition = ProductCondition.UNDETERMINED
    seller_name: str | None = None
    is_available: bool = True
    source_website_id: int
    source_metadata: dict | None = None


class ProductAttributesForUpdate(BaseModel):
    """Attributes for product update - all fields optional."""

    url: str | None = None
    title: str | None = None
    source_product_code: str | None = None
    description: str | None = None
    image_urls: str | None = None
    city: str | None = None
    state: str | None = None
    condition: ProductCondition | None = None
    seller_name: str | None = None
    is_available: bool | None = None
    source_website_id: int | None = None
    source_metadata: dict | None = None


class ProductResource(ResourceObject):
    """Product resource following JSON:API specification."""

    type: str = Field(default="products", examples=["products"])
    attributes: ProductAttributes

    @classmethod
    def from_entity(cls, entity) -> "ProductResource":
        """
        Factory method: converts a ProductEntity to ProductResource JSON:API.
        """
        return cls.from_model(
            entity,
            type_name="products",
            attributes_field=ProductAttributes,
        )


class ProductResourceForCreation(ResourceObjectForCreation):
    """ResourceObject for product creation (without id)."""

    type: str = Field(default="products", examples=["products"])
    attributes: ProductAttributesForCreation


class ProductResourceForUpdate(ResourceObjectForCreation):
    """ResourceObject for product update (without id)."""

    type: str = Field(default="products", examples=["products"])
    attributes: ProductAttributesForUpdate


class ProductCreateRequest(SingleResourceRequest):
    """Request schema for creating a product."""

    data: ProductResourceForCreation


class ProductUpdateRequest(SingleResourceRequest):
    """Request schema for updating a product."""

    data: ProductResourceForUpdate


class ProductReadResponse(SingleResourceResponse):
    """Response schema for a single product."""

    data: ProductResource


class ProductsCollectionResponse(CollectionResponse):
    """Response schema for a collection of products."""

    data: list[ProductResource]
