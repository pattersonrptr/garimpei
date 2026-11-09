from datetime import datetime

from pydantic import BaseModel, Field

from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    SingleResourceResponse,
)


class NotificationLogAttributes(BaseModel):
    """Notification log attributes for responses."""

    price_alert_id: int
    user_id: int
    product_id: int | None = None
    email_to: str
    subject: str
    status: str
    error_message: str | None = None
    sent_at: datetime | None = None
    created_at: datetime | None = None


class NotificationLogResource(ResourceObject):
    """Notification log resource following JSON:API specification."""

    type: str = Field(default="notification_logs", examples=["notification_logs"])
    attributes: NotificationLogAttributes

    @classmethod
    def from_entity(cls, entity) -> "NotificationLogResource":
        """Factory method: converts a NotificationLogEntity to NotificationLogResource."""
        return cls.from_model(
            entity,
            type_name="notification_logs",
            attributes_field=NotificationLogAttributes,
        )


class NotificationLogReadResponse(SingleResourceResponse):
    """Response schema for a single notification log."""

    data: NotificationLogResource


class NotificationLogsCollectionResponse(CollectionResponse):
    """Response schema for a collection of notification logs."""

    data: list[NotificationLogResource]
