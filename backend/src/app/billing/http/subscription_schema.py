from datetime import datetime

from pydantic import BaseModel, Field

from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    SingleResourceResponse,
)


class SubscriptionAttributes(BaseModel):
    user_id: int
    plan_id: int
    plan_name: str | None = None
    status: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    canceled_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SubscriptionResource(ResourceObject):
    type: str = Field(default="subscriptions")
    attributes: SubscriptionAttributes

    @classmethod
    def from_entity(
        cls, entity, plan_name: str | None = None
    ) -> "SubscriptionResource":
        attrs = SubscriptionAttributes(
            user_id=entity.user_id,
            plan_id=entity.plan_id,
            plan_name=plan_name,
            status=entity.status,
            current_period_start=entity.current_period_start,
            current_period_end=entity.current_period_end,
            canceled_at=entity.canceled_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        return cls(
            type="subscriptions",
            id=str(entity.id) if entity.id else None,
            attributes=attrs,
        )


class SubscriptionReadResponse(SingleResourceResponse):
    data: SubscriptionResource


class SubscriptionsCollectionResponse(CollectionResponse):
    data: list[SubscriptionResource]  # type: ignore[assignment]
