from datetime import datetime, time

from pydantic import BaseModel, Field

from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class SearchConfigAttributes(BaseModel):
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


class SearchConfigAttributesForCreation(BaseModel):
    """Attributes for search config creation."""

    search_term: str
    user_id: int
    is_active: bool = True
    frequency_days: int = 1
    preferred_time: time = time(0, 0)
    search_metadata: dict | None = None
    source_website_ids: list[int] = Field(default_factory=list)


class SearchConfigAttributesForUpdate(BaseModel):
    """Attributes for search config update — all optional."""

    search_term: str | None = None
    is_active: bool | None = None
    frequency_days: int | None = None
    preferred_time: time | None = None
    search_metadata: dict | None = None
    source_website_ids: list[int] | None = None


class SearchConfigResource(ResourceObject):
    """Search config resource following JSON:API specification."""

    type: str = Field(default="search_configs", examples=["search_configs"])
    attributes: SearchConfigAttributes

    @classmethod
    def from_entity(cls, entity) -> "SearchConfigResource":
        """Factory method: converts a SavedSearch to SearchConfigResource."""
        return cls.from_model(
            entity,
            type_name="search_configs",
            attributes_field=SearchConfigAttributes,
        )


class SearchConfigResourceForCreation(ResourceObjectForCreation):
    """ResourceObject for search config creation (without id)."""

    type: str = Field(default="search_config", examples=["search_config"])
    attributes: SearchConfigAttributesForCreation


class SearchConfigResourceForUpdate(ResourceObjectForCreation):
    """ResourceObject for search config update (without id)."""

    type: str = Field(default="search_config", examples=["search_config"])
    attributes: SearchConfigAttributesForUpdate


class SearchConfigCreateRequest(SingleResourceRequest):
    """Request schema for creating a search config."""

    data: SearchConfigResourceForCreation


class SearchConfigUpdateRequest(SingleResourceRequest):
    """Request schema for updating a search config."""

    data: SearchConfigResourceForUpdate


class SearchConfigReadResponse(SingleResourceResponse):
    """Response schema for a single search config."""

    data: SearchConfigResource


class SearchConfigsCollectionResponse(CollectionResponse):
    """Response schema for a collection of search configs."""

    data: list[SearchConfigResource]
