from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SearchExecutionStatus = Literal["pending", "running", "success", "failed"]


class SearchExecutionLog(BaseModel):
    """SearchExecutionLog domain entity representing a single execution of a search config."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    search_config_id: int
    status: SearchExecutionStatus = "pending"
    results_count: int | None = None  # listings that matched the search term
    listings_found: int | None = None  # listings the sites returned
    listings_checked: int | None = None  # listings scraped so far
    error_message: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
