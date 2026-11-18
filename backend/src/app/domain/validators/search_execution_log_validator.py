from src.app.searches.ports import (
    SavedSearchRepositoryInterface,
    SearchRunRepositoryInterface,
)
from src.common.jsonapi import JsonApiError

VALID_STATUSES = {"pending", "running", "success", "failed"}


class SearchExecutionLogValidator:
    """Validates search execution log create requests."""

    def __init__(
        self,
        search_execution_log_repo: SearchRunRepositoryInterface,
        search_config_repo: SavedSearchRepositoryInterface,
    ):
        self.search_execution_log_repo = search_execution_log_repo
        self.search_config_repo = search_config_repo

    def validate_create_request(self, search_execution_log_in) -> list[JsonApiError]:
        """
        Validates a search execution log creation request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "search_execution_log"
        if search_execution_log_in.data.type != "search_execution_log":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=(
                        f"Expected type 'search_execution_log', "
                        f"got '{search_execution_log_in.data.type}'"
                    ),
                    source={"pointer": "/data/type"},
                )
            )

        attrs = search_execution_log_in.data.attributes

        # Validation 2: search_config_id required and positive
        if attrs.search_config_id is None or attrs.search_config_id <= 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'search_config_id' must be a positive integer",
                    source={"pointer": "/data/attributes/search_config_id"},
                )
            )

        # Validation 3: status must be one of the valid values (if provided)
        if attrs.status is not None and attrs.status not in VALID_STATUSES:
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_FIELD",
                    title="Validation error",
                    detail=(
                        f"Field 'status' must be one of: "
                        f"{', '.join(sorted(VALID_STATUSES))}"
                    ),
                    source={"pointer": "/data/attributes/status"},
                )
            )

        # Validation 4: results_count must be non-negative (if provided)
        if attrs.results_count is not None and attrs.results_count < 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_FIELD",
                    title="Validation error",
                    detail="Field 'results_count' must be a non-negative integer",
                    source={"pointer": "/data/attributes/results_count"},
                )
            )

        # Return early if field-level errors
        if errors:
            return errors

        # Validation 5: referenced search_config must exist
        existing_config = self.search_config_repo.get_by_id(attrs.search_config_id)
        if not existing_config:
            errors.append(
                JsonApiError(
                    status="404",
                    code="SEARCH_CONFIG_NOT_FOUND",
                    title="Related resource not found",
                    detail=(
                        f"SearchConfig with id '{attrs.search_config_id}' does not exist"
                    ),
                    source={"pointer": "/data/attributes/search_config_id"},
                )
            )

        return errors
