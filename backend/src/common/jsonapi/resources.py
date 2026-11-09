import builtins
from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class ResourceIdentifier(BaseModel):
    type: str
    id: str | None = None


class ResourceObject(BaseModel):
    type: str = Field(..., description="Resource type identifier")
    id: str | None = None
    attributes: Any = None
    relationships: dict[str, Any] | None = None

    @classmethod
    def from_model(
        cls,
        model: Any,
        type_name: str,
        attributes_field: builtins.type[T] | None = None,
        exclude: list[str] | None = None,
    ) -> "ResourceObject":
        """
        Builds a ResourceObject from an entity/model.
        - model: pydantic model or object with __dict__.
        - type_name: fixed value for 'type' field (e.g., "users").
        - attributes_field: if provided, instantiates this BaseModel with attribute data.
        - exclude: list of fields to exclude from attributes (e.g., ['hashed_password']).
        """
        exclude = exclude or []

        # Extract data from entity (support pydantic and regular objects)
        if hasattr(model, "model_dump"):
            attrs = model.model_dump(exclude_unset=True)
        else:
            attrs = {
                k: v
                for k, v in getattr(model, "__dict__", {}).items()
                if not k.startswith("_")
            }

        entity_id = attrs.get("id")

        # Prepare attributes data (removing id and excluded fields)
        attributes_data = {
            k: v for k, v in attrs.items() if k not in exclude and k != "id"
        }

        if attributes_field:
            attributes = attributes_field(**attributes_data)
        else:
            attributes = attributes_data

        return cls(
            type=type_name,
            id=str(entity_id) if entity_id is not None else None,
            attributes=attributes,
        )


class ResourceObjectForCreation(BaseModel):
    """ResourceObject for creation requests (POST) - without id field"""

    type: str = Field(..., description="Resource type identifier")
    attributes: Any = None
    relationships: dict[str, Any] | None = None


class SingleResourceRequest(BaseModel):
    data: ResourceObjectForCreation


class SingleResourceResponse(BaseModel):
    data: ResourceObject


class CollectionResponse(BaseModel):
    data: list[ResourceObject]
    meta: dict[str, Any] | None = None
    links: dict[str, str] | None = None
