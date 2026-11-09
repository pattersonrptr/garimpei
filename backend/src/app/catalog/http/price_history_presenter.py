from fastapi.responses import JSONResponse

from src.app.catalog.entities import PriceHistory as PriceHistoryEntity
from src.app.catalog.http.price_history_schema import (
    PriceHistoriesCollectionResponse,
    PriceHistoryReadResponse,
    PriceHistoryResource,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class PriceHistoryPresenter:
    """
    Presenter for PriceHistory entities following Clean Architecture.
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
                title="Price history record not found",
                detail=f"Price history record with {identifier} not found",
                source={"pointer": pointer},
            )
        ]
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_success(entity: PriceHistoryEntity) -> PriceHistoryReadResponse:
        """Returns price history record in JSON:API format (success)."""
        return PriceHistoryReadResponse(data=PriceHistoryResource.from_entity(entity))

    @staticmethod
    def handle_collection_success(
        entities: list[PriceHistoryEntity], total: int
    ) -> PriceHistoriesCollectionResponse:
        """Returns collection of price history records in JSON:API format."""
        return PriceHistoriesCollectionResponse(
            data=[PriceHistoryResource.from_entity(entity) for entity in entities],
            meta={"total": total},
        )
