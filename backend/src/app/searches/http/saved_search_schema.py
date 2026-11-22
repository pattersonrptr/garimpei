from datetime import datetime, time

from pydantic import BaseModel, Field

from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class SavedSearchAttributes(BaseModel):
    """Search config attributes for responses."""

    search_term: str
    is_active: bool
    frequency_days: int
    preferred_time: time
    search_metadata: dict | None = None
    user_id: int | None = None
    source_website_ids: list[int] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SavedSearchAttributesForCreation(BaseModel):
    """Attributes for search config creation."""

    search_term: str
    user_id: int
    is_active: bool = True
    frequency_days: int = 1
    preferred_time: time = time(0, 0)
    search_metadata: dict | None = None
    source_website_ids: list[int] = Field(default_factory=list)


class SavedSearchAttributesForUpdate(BaseModel):
    """Attributes for search config update — all optional."""

    search_term: str | None = None
    is_active: bool | None = None
    frequency_days: int | None = None
    preferred_time: time | None = None
    search_metadata: dict | None = None
    source_website_ids: list[int] | None = None


class SavedSearchResource(ResourceObject):
    """Search config resource following JSON:API specification."""

    type: str = Field(default="search_configs", examples=["search_configs"])
    attributes: SavedSearchAttributes

    @classmethod
    def from_entity(cls, entity) -> "SavedSearchResource":
        """Factory method: converts a SavedSearch to SavedSearchResource."""
        return cls.from_model(
            entity,
            type_name="search_configs",
            attributes_field=SavedSearchAttributes,
        )


class SavedSearchResourceForCreation(ResourceObjectForCreation):
    """ResourceObject for search config creation (without id)."""

    type: str = Field(default="search_config", examples=["search_config"])
    attributes: SavedSearchAttributesForCreation


class SavedSearchResourceForUpdate(ResourceObjectForCreation):
    """ResourceObject for search config update (without id)."""

    type: str = Field(default="search_config", examples=["search_config"])
    attributes: SavedSearchAttributesForUpdate


class SavedSearchCreateRequest(SingleResourceRequest):
    """Request schema for creating a search config."""

    data: SavedSearchResourceForCreation


class SavedSearchUpdateRequest(SingleResourceRequest):
    """Request schema for updating a search config."""

    data: SavedSearchResourceForUpdate


class SavedSearchReadResponse(SingleResourceResponse):
    """Response schema for a single search config."""

    data: SavedSearchResource


class SavedSearchesCollectionResponse(CollectionResponse):
    """Response schema for a collection of search configs."""

    data: list[SavedSearchResource]  # type: ignore[assignment]
