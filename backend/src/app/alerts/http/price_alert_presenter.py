from fastapi.responses import JSONResponse

from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.http.price_alert_schema import (
    PriceAlertReadResponse,
    PriceAlertResource,
    PriceAlertsCollectionResponse,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class PriceAlertPresenter:
    """
    Presenter for PriceAlert entities following Clean Architecture.
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
                title="Price alert not found",
                detail=f"Price alert with {identifier} not found",
                source={"pointer": pointer},
            )
        ]
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_success(entity: PriceAlertEntity) -> PriceAlertReadResponse:
        """Returns price alert in JSON:API format (success)."""
        return PriceAlertReadResponse(data=PriceAlertResource.from_entity(entity))

    @staticmethod
    def handle_collection_success(
        entities: list[PriceAlertEntity], total: int
    ) -> PriceAlertsCollectionResponse:
        """Returns collection of price alerts in JSON:API format."""
        return PriceAlertsCollectionResponse(
            data=[PriceAlertResource.from_entity(entity) for entity in entities],
            meta={"total": total},
        )
