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


class SearchExecutionLogAttributes(BaseModel):
    """Search execution log attributes for responses."""

    search_config_id: int
    status: str
    results_count: int | None = None
    listings_found: int | None = None
    listings_checked: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class SearchExecutionLogAttributesForCreation(BaseModel):
    """Attributes for search execution log creation."""

    search_config_id: int
    status: str = "pending"
    results_count: int | None = None
    listings_found: int | None = None
    listings_checked: int | None = None
    error_message: str | None = None


class SearchExecutionLogAttributesForUpdate(BaseModel):
    """Attributes a scraper may change while a run progresses (all optional)."""

    status: Literal["pending", "running", "success", "failed"] | None = None
    results_count: int | None = None
    listings_found: int | None = None
    listings_checked: int | None = None
    error_message: str | None = None


class SearchExecutionLogResourceForCreation(ResourceObjectForCreation):
    """ResourceObject for search execution log creation (without id)."""

    type: str = Field(
        default="search_execution_logs", examples=["search_execution_logs"]
    )
    attributes: SearchExecutionLogAttributesForCreation


class SearchExecutionLogCreateRequest(SingleResourceRequest):
    """Request schema for creating a search execution log."""

    data: SearchExecutionLogResourceForCreation


class SearchExecutionLogResourceForUpdate(BaseModel):
    """ResourceObject for a partial update."""

    type: str = Field(
        default="search_execution_logs", examples=["search_execution_logs"]
    )
    id: str | None = None
    attributes: SearchExecutionLogAttributesForUpdate


class SearchExecutionLogUpdateRequest(BaseModel):
    """Request schema for updating a search execution log."""

    data: SearchExecutionLogResourceForUpdate


class SearchExecutionLogResource(ResourceObject):
    """Search execution log resource following JSON:API specification."""

    type: str = Field(
        default="search_execution_logs", examples=["search_execution_logs"]
    )
    attributes: SearchExecutionLogAttributes

    @classmethod
    def from_entity(cls, entity) -> "SearchExecutionLogResource":
        """Factory method: converts a SearchExecutionLogEntity to SearchExecutionLogResource."""
        return cls.from_model(
            entity,
            type_name="search_execution_logs",
            attributes_field=SearchExecutionLogAttributes,
        )


class SearchExecutionLogReadResponse(SingleResourceResponse):
    """Response schema for a single search execution log."""

    data: SearchExecutionLogResource


class SearchExecutionLogsCollectionResponse(CollectionResponse):
    """Response schema for a collection of search execution logs."""

    data: list[SearchExecutionLogResource]
