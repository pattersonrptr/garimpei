from src.app.stores.ports import StoreRepositoryInterface
from src.common.jsonapi import JsonApiError


class SourceWebsiteValidator:
    def __init__(self, source_website_repo: StoreRepositoryInterface):
        self.source_website_repo = source_website_repo

    def validate_create_request(self, source_website_in) -> list[JsonApiError]:
        """
        Validates a source website creation request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "source_website"
        if source_website_in.data.type != "source_website":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'source_website', got '{source_website_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = source_website_in.data.attributes

        # Validation 2: name required
        if not attrs.name or not attrs.name.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'name' is required",
                    source={"pointer": "/data/attributes/name"},
                )
            )

        # Validation 3: base_url required
        if not attrs.base_url or not attrs.base_url.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'base_url' is required",
                    source={"pointer": "/data/attributes/base_url"},
                )
            )

        # If required field errors, return early
        if errors:
            return errors

        # Validation 4: name must be unique
        existing = self.source_website_repo.get_by_name(attrs.name)
        if existing:
            errors.append(
                JsonApiError(
                    status="409",
                    code="DUPLICATE_NAME",
                    title="Conflict",
                    detail=f"A source website with name '{attrs.name}' already exists",
                    source={"pointer": "/data/attributes/name"},
                )
            )

        return errors

    def validate_update_request(
        self, source_website_id: int, source_website_in
    ) -> list[JsonApiError]:
        """
        Validates a source website update request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "source_website"
        if source_website_in.data.type != "source_website":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'source_website', got '{source_website_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = source_website_in.data.attributes

        # Validation 2: name cannot be empty if provided
        if attrs.name is not None and not attrs.name.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_VALUE",
                    title="Validation error",
                    detail="Field 'name' cannot be empty",
                    source={"pointer": "/data/attributes/name"},
                )
            )

        # Validation 3: base_url cannot be empty if provided
        if attrs.base_url is not None and not attrs.base_url.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="INVALID_VALUE",
                    title="Validation error",
                    detail="Field 'base_url' cannot be empty",
                    source={"pointer": "/data/attributes/base_url"},
                )
            )

        # If there are format errors, return early
        if errors:
            return errors

        # Validation 4: new name must not conflict with another record
        if attrs.name is not None:
            existing = self.source_website_repo.get_by_name(attrs.name)
            if existing and existing.id != source_website_id:
                errors.append(
                    JsonApiError(
                        status="409",
                        code="DUPLICATE_NAME",
                        title="Conflict",
                        detail=f"A source website with name '{attrs.name}' already exists",
                        source={"pointer": "/data/attributes/name"},
                    )
                )

        return errors
