from datetime import datetime

from pydantic import BaseModel, Field

from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class StoreAttributes(BaseModel):
    """Source website attributes for responses."""

    name: str
    base_url: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StoreAttributesForCreation(BaseModel):
    """Attributes for source website creation."""

    name: str
    base_url: str
    is_active: bool = True


class StoreAttributesForUpdate(BaseModel):
    """Attributes for source website update — all fields optional."""

    name: str | None = None
    base_url: str | None = None
    is_active: bool | None = None


class StoreResource(ResourceObject):
    """Source website resource following JSON:API specification."""

    type: str = Field(default="source_websites", examples=["source_websites"])
    attributes: StoreAttributes

    @classmethod
    def from_entity(cls, entity) -> "StoreResource":
        """Factory method: converts a StoreEntity to StoreResource."""
        return cls.from_model(
            entity,
            type_name="source_websites",
            attributes_field=StoreAttributes,
        )


class StoreResourceForCreation(ResourceObjectForCreation):
    """ResourceObject for source website creation (without id)."""

    type: str = Field(default="source_websites", examples=["source_websites"])
    attributes: StoreAttributesForCreation


class StoreResourceForUpdate(ResourceObjectForCreation):
    """ResourceObject for source website update (without id)."""

    type: str = Field(default="source_websites", examples=["source_websites"])
    attributes: StoreAttributesForUpdate


class StoreCreateRequest(SingleResourceRequest):
    """Request schema for creating a source website."""

    data: StoreResourceForCreation


class StoreUpdateRequest(SingleResourceRequest):
    """Request schema for updating a source website."""

    data: StoreResourceForUpdate


class StoreReadResponse(SingleResourceResponse):
    """Response schema for a single source website."""

    data: StoreResource


class StoresCollectionResponse(CollectionResponse):
    """Response schema for a collection of source websites."""

    data: list[StoreResource]  # type: ignore[assignment]
