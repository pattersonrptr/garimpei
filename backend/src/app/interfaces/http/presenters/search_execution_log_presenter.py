from fastapi.responses import JSONResponse

from src.app.interfaces.http.schemas.search_execution_log_schema import (
    SearchExecutionLogReadResponse,
    SearchExecutionLogResource,
    SearchExecutionLogsCollectionResponse,
)
from src.app.searches.entities import SearchRun
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class SearchExecutionLogPresenter:
    """
    Presenter for SearchExecutionLog entities following Clean Architecture.
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
    ) -> SearchExecutionLogReadResponse:
        """Returns search execution log in JSON:API format (success)."""
        return SearchExecutionLogReadResponse(
            data=SearchExecutionLogResource.from_entity(entity)
        )

    @staticmethod
    def handle_collection_success(
        entities: list[SearchRun], total: int
    ) -> SearchExecutionLogsCollectionResponse:
        """Returns collection of search execution logs in JSON:API format."""
        return SearchExecutionLogsCollectionResponse(
            data=[SearchExecutionLogResource.from_entity(e) for e in entities],
            meta={"total": total},
        )
