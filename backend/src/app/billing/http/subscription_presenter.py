from fastapi.responses import JSONResponse

from src.app.billing.http.subscription_schema import (
    SubscriptionReadResponse,
    SubscriptionResource,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class SubscriptionPresenter:
    @staticmethod
    def handle_success(
        entity, plan_name: str | None = None
    ) -> SubscriptionReadResponse:
        return SubscriptionReadResponse(
            data=SubscriptionResource.from_entity(entity, plan_name=plan_name)
        )

    @staticmethod
    def handle_not_found(identifier: str) -> JSONResponse:
        errors = [
            JsonApiError(
                status="404",
                code="NOT_FOUND",
                title="Subscription not found",
                detail=f"Subscription with {identifier} not found",
                source={"pointer": "/data"},
            )
        ]
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_error(status: int, code: str, title: str, detail: str) -> JSONResponse:
        errors = [
            JsonApiError(
                status=str(status),
                code=code,
                title=title,
                detail=detail,
                source={"pointer": "/data"},
            )
        ]
        return JSONResponse(
            status_code=status,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )
