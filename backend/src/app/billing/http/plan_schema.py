from pydantic import BaseModel, Field

from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class PlanAttributes(BaseModel):
    name: str
    display_name: str
    price_cents: int
    max_active_alerts: int | None = None
    min_frequency_minutes: int
    price_history_days: int | None = None
    max_sources: int | None = None
    has_push_notifications: bool
    has_whatsapp_notifications: bool
    has_api_access: bool
    is_active: bool


class PlanResource(ResourceObject):
    type: str = Field(default="plans")
    attributes: PlanAttributes

    @classmethod
    def from_entity(cls, entity) -> "PlanResource":
        return cls.from_model(
            entity, type_name="plans", attributes_field=PlanAttributes
        )


class PlanReadResponse(SingleResourceResponse):
    data: PlanResource


class PlansCollectionResponse(CollectionResponse):
    data: list[PlanResource]  # type: ignore[assignment]


class PlanAttributesForCreation(BaseModel):
    name: str
    display_name: str
    price_cents: int = 0
    max_active_alerts: int | None = None
    min_frequency_minutes: int = 360
    price_history_days: int | None = 7
    max_sources: int | None = None
    has_push_notifications: bool = False
    has_whatsapp_notifications: bool = False
    has_api_access: bool = False


class PlanResourceForCreation(ResourceObjectForCreation):
    type: str = Field(default="plan")
    attributes: PlanAttributesForCreation


class PlanCreateRequest(SingleResourceRequest):
    data: PlanResourceForCreation
