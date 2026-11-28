from fastapi.responses import JSONResponse

from src.app.stores.entities import Store
from src.app.stores.http.store_schema import (
    StoreReadResponse,
    StoreResource,
    StoresCollectionResponse,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class StorePresenter:
    """
    Presenter for Store entities following Clean Architecture.
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
                title="Source website not found",
                detail=f"Source website with {identifier} not found",
                source={"pointer": pointer},
            )
        ]
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_has_offers() -> JSONResponse:
        """Returns 409 in JSON:API format: the store still has offers."""
        errors = [
            JsonApiError(
                status="409",
                code="STORE_HAS_OFFERS",
                title="Source website has offers",
                detail=("The source website still has offers; deactivate it instead."),
            )
        ]
        return JSONResponse(
            status_code=409,
            content=JsonApiErrorResponse(errors=errors).model_dump(exclude_none=True),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_success(entity: Store) -> StoreReadResponse:
        """Returns source website in JSON:API format (success)."""
        return StoreReadResponse(data=StoreResource.from_entity(entity))

    @staticmethod
    def handle_collection_success(
        entities: list[Store], total: int
    ) -> StoresCollectionResponse:
        """Returns collection of source websites in JSON:API format."""
        return StoresCollectionResponse(
            data=[StoreResource.from_entity(entity) for entity in entities],
            meta={"total": total},
        )
