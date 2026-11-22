from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class SearchRunAttributes(BaseModel):
    """Search execution log attributes for responses."""

    search_config_id: int
    status: str
    results_count: int | None = None
    listings_found: int | None = None
    listings_checked: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class SearchRunAttributesForCreation(BaseModel):
    """Attributes for search execution log creation."""

    search_config_id: int
    status: str = "pending"
    results_count: int | None = None
    listings_found: int | None = None
    listings_checked: int | None = None
    error_message: str | None = None


class SearchRunAttributesForUpdate(BaseModel):
    """Attributes a scraper may change while a run progresses (all optional)."""

    status: Literal["pending", "running", "success", "failed"] | None = None
    results_count: int | None = None
    listings_found: int | None = None
    listings_checked: int | None = None
    error_message: str | None = None


class SearchRunResourceForCreation(ResourceObjectForCreation):
    """ResourceObject for search execution log creation (without id)."""

    type: str = Field(
        default="search_execution_logs", examples=["search_execution_logs"]
    )
    attributes: SearchRunAttributesForCreation


class SearchRunCreateRequest(SingleResourceRequest):
    """Request schema for creating a search execution log."""

    data: SearchRunResourceForCreation


class SearchRunResourceForUpdate(BaseModel):
    """ResourceObject for a partial update."""

    type: str = Field(
        default="search_execution_logs", examples=["search_execution_logs"]
    )
    id: str | None = None
    attributes: SearchRunAttributesForUpdate


class SearchRunUpdateRequest(BaseModel):
    """Request schema for updating a search execution log."""

    data: SearchRunResourceForUpdate


class SearchRunResource(ResourceObject):
    """Search execution log resource following JSON:API specification."""

    type: str = Field(
        default="search_execution_logs", examples=["search_execution_logs"]
    )
    attributes: SearchRunAttributes

    @classmethod
    def from_entity(cls, entity) -> "SearchRunResource":
        """Factory method: converts a SearchRun to SearchRunResource."""
        return cls.from_model(
            entity,
            type_name="search_execution_logs",
            attributes_field=SearchRunAttributes,
        )


class SearchRunReadResponse(SingleResourceResponse):
    """Response schema for a single search execution log."""

    data: SearchRunResource


class SearchRunsCollectionResponse(CollectionResponse):
    """Response schema for a collection of search execution logs."""

    data: list[SearchRunResource]  # type: ignore[assignment]
