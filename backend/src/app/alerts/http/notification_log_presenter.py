from fastapi.responses import JSONResponse

from src.app.alerts.entities import NotificationLog as NotificationLogEntity
from src.app.alerts.http.notification_log_schema import (
    NotificationLogReadResponse,
    NotificationLogResource,
    NotificationLogsCollectionResponse,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class NotificationLogPresenter:
    """
    Presenter for NotificationLog entities following Clean Architecture.
    Transforms domain entities into HTTP presentation formats (JSON:API).
    """

    @staticmethod
    def handle_not_found(identifier: str, pointer: str = "/data") -> JSONResponse:
        """Returns 404 in JSON:API format."""
        errors = [
            JsonApiError(
                status="404",
                code="NOT_FOUND",
                title="Notification log not found",
                detail=f"Notification log with {identifier} not found",
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
        entity: NotificationLogEntity,
    ) -> NotificationLogReadResponse:
        """Returns notification log in JSON:API format (success)."""
        return NotificationLogReadResponse(
            data=NotificationLogResource.from_entity(entity)
        )

    @staticmethod
    def handle_collection_success(
        entities: list[NotificationLogEntity], total: int
    ) -> NotificationLogsCollectionResponse:
        """Returns collection of notification logs in JSON:API format."""
        return NotificationLogsCollectionResponse(
            data=[NotificationLogResource.from_entity(e) for e in entities],
            meta={"total": total},
        )
