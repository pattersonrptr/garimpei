from fastapi.responses import JSONResponse

from src.app.searches.entities import SearchRun
from src.app.searches.http.search_run_schema import (
    SearchRunReadResponse,
    SearchRunResource,
    SearchRunsCollectionResponse,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class SearchRunPresenter:
    """
    Presenter for SearchRun entities following Clean Architecture.
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
                title="Search execution log not found",
                detail=f"Search execution log with {identifier} not found",
                source={"pointer": pointer},
            )
        ]
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_success(
        entity: SearchRun,
    ) -> SearchRunReadResponse:
        """Returns search execution log in JSON:API format (success)."""
        return SearchRunReadResponse(data=SearchRunResource.from_entity(entity))

    @staticmethod
    def handle_collection_success(
        entities: list[SearchRun], total: int
    ) -> SearchRunsCollectionResponse:
        """Returns collection of search execution logs in JSON:API format."""
        return SearchRunsCollectionResponse(
            data=[SearchRunResource.from_entity(e) for e in entities],
            meta={"total": total},
        )
