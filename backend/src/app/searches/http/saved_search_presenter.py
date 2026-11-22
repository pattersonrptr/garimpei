from fastapi.responses import JSONResponse

from src.app.searches.entities import SavedSearch
from src.app.searches.http.saved_search_schema import (
    SavedSearchesCollectionResponse,
    SavedSearchReadResponse,
    SavedSearchResource,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class SavedSearchPresenter:
    """
    Presenter for SavedSearch entities following Clean Architecture.
    Transforms domain entities into HTTP presentation formats (JSON:API).
    """

    @staticmethod
    def handle_validation_errors(validation_errors: list) -> JSONResponse:
        """Returns validation errors in JSON:API format."""
        first_error = validation_errors[0]
        status_code = int(first_error.status)
        return JSONResponse(
            status_code=status_code,
            content=JsonApiErrorResponse(errors=validation_errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_not_found(identifier: str, pointer: str = "/data") -> JSONResponse:
        """Returns 404 in JSON:API format."""
        errors = [
            JsonApiError(
                status="404",
                code="NOT_FOUND",
                title="Search config not found",
                detail=f"Search config with {identifier} not found",
                source={"pointer": pointer},
            )
        ]
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_success(entity: SavedSearch) -> SavedSearchReadResponse:
        """Returns search config in JSON:API format (success)."""
        return SavedSearchReadResponse(data=SavedSearchResource.from_entity(entity))

    @staticmethod
    def handle_collection_success(
        entities: list[SavedSearch], total: int
    ) -> SavedSearchesCollectionResponse:
        """Returns collection of search configs in JSON:API format."""
        return SavedSearchesCollectionResponse(
            data=[SavedSearchResource.from_entity(entity) for entity in entities],
            meta={"total": total},
        )
