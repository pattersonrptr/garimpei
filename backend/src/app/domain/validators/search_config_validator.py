from src.app.interfaces.repositories.search_config_repository import (
    SearchConfigRepositoryInterface,
)
from src.app.stores.ports import StoreRepositoryInterface
from src.common.jsonapi import JsonApiError


class SearchConfigValidator:
    """Validates search config create and update requests."""

    def __init__(
        self,
        search_config_repo: SearchConfigRepositoryInterface,
        source_website_repo: StoreRepositoryInterface,
    ):
        self.search_config_repo = search_config_repo
        self.source_website_repo = source_website_repo

    def validate_create_request(self, search_config_in) -> list[JsonApiError]:
        """
        Validates a search config creation request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "search_config"
        if search_config_in.data.type != "search_config":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'search_config', got '{search_config_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = search_config_in.data.attributes

        # Validation 2: search_term required and non-empty
        if not attrs.search_term or not attrs.search_term.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'search_term' is required",
                    source={"pointer": "/data/attributes/search_term"},
                )
            )

        # Validation 3: user_id required
        if attrs.user_id is None:
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'user_id' is required",
                    source={"pointer": "/data/attributes/user_id"},
                )
            )

        # Validation 4: frequency_days must be positive if provided
        if attrs.frequency_days is not None and attrs.frequency_days <= 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_FIELD",
                    title="Validation error",
                    detail="Field 'frequency_days' must be a positive integer",
                    source={"pointer": "/data/attributes/frequency_days"},
                )
            )

        # Return early if field-level errors
        if errors:
            return errors

        # Validation 5: each source_website_id must exist
        for sw_id in attrs.source_website_ids or []:
            existing_sw = self.source_website_repo.get_by_id(sw_id)
            if not existing_sw:
                errors.append(
                    JsonApiError(
                        status="404",
                        code="SOURCE_WEBSITE_NOT_FOUND",
                        title="Related resource not found",
                        detail=f"SourceWebsite with id '{sw_id}' does not exist",
                        source={"pointer": "/data/attributes/source_website_ids"},
                    )
                )

        if errors:
            return errors

        # Validation 6: search_term must be unique per user_id
        existing = self.search_config_repo.get_by_search_term_and_user_id(
            attrs.search_term, attrs.user_id
        )
        if existing:
            errors.append(
                JsonApiError(
                    status="409",
                    code="DUPLICATE_SEARCH_TERM",
                    title="Conflict",
                    detail=f"A search config with term '{attrs.search_term}' already exists for this user",
                    source={"pointer": "/data/attributes/search_term"},
                )
            )

        return errors

    def validate_update_request(
        self, search_config_id: int, search_config_in
    ) -> list[JsonApiError]:
        """
        Validates a search config update request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "search_config"
        if search_config_in.data.type != "search_config":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'search_config', got '{search_config_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = search_config_in.data.attributes

        # Validation 2: search_term cannot be empty if provided
        if attrs.search_term is not None and not attrs.search_term.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_VALUE",
                    title="Validation error",
                    detail="Field 'search_term' cannot be empty",
                    source={"pointer": "/data/attributes/search_term"},
                )
            )

        # Validation 3: frequency_days must be positive if provided
        if attrs.frequency_days is not None and attrs.frequency_days <= 0:
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_FIELD",
                    title="Validation error",
                    detail="Field 'frequency_days' must be a positive integer",
                    source={"pointer": "/data/attributes/frequency_days"},
                )
            )

        # Return early if field-level errors
        if errors:
            return errors

        # Validation 4: each source_website_id must exist
        for sw_id in attrs.source_website_ids or []:
            existing_sw = self.source_website_repo.get_by_id(sw_id)
            if not existing_sw:
                errors.append(
                    JsonApiError(
                        status="404",
                        code="SOURCE_WEBSITE_NOT_FOUND",
                        title="Related resource not found",
                        detail=f"SourceWebsite with id '{sw_id}' does not exist",
                        source={"pointer": "/data/attributes/source_website_ids"},
                    )
                )

        if errors:
            return errors

        # Validation 5: search_term uniqueness per user (only when search_term is being updated)
        if attrs.search_term is not None:
            existing_config = self.search_config_repo.get_by_id(search_config_id)
            if existing_config:
                user_id = existing_config.user_id
                duplicate = self.search_config_repo.get_by_search_term_and_user_id(
                    attrs.search_term, user_id
                )
                if duplicate and duplicate.id != search_config_id:
                    errors.append(
                        JsonApiError(
                            status="409",
                            code="DUPLICATE_SEARCH_TERM",
                            title="Conflict",
                            detail=f"A search config with term '{attrs.search_term}' already exists for this user",
                            source={"pointer": "/data/attributes/search_term"},
                        )
                    )

        return errors
