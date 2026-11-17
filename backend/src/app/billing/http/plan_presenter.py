from fastapi.responses import JSONResponse

from src.app.billing.entities import Plan as PlanEntity
from src.app.billing.http.plan_schema import (
    PlanReadResponse,
    PlanResource,
    PlansCollectionResponse,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class PlanPresenter:
    @staticmethod
    def handle_success(entity: PlanEntity) -> PlanReadResponse:
        return PlanReadResponse(data=PlanResource.from_entity(entity))

    @staticmethod
    def handle_collection_success(
        entities: list[PlanEntity],
    ) -> PlansCollectionResponse:
        return PlansCollectionResponse(
            data=[PlanResource.from_entity(e) for e in entities],
            meta={"total": len(entities)},
        )

    @staticmethod
    def handle_not_found(identifier: str) -> JSONResponse:
        errors = [
            JsonApiError(
                status="404",
                code="NOT_FOUND",
                title="Plan not found",
                detail=f"Plan with {identifier} not found",
                source={"pointer": "/data"},
            )
        ]
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )
