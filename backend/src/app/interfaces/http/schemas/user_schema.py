from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from src.app.accounts.use_cases import NewUser, UserChanges
from src.common.jsonapi import (
    CollectionResponse,
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class UserAttributes(BaseModel):
    username: str
    email: EmailStr
    is_active: bool | None = True
    is_staff: bool | None = False
    is_superuser: bool | None = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserAttributesForCreation(BaseModel):
    """Attributes for creation - with password, without timestamps"""

    username: str
    email: EmailStr
    password: str
    is_active: bool | None = True
    is_staff: bool | None = False
    is_superuser: bool | None = False

    def to_new_user(self) -> NewUser:
        """The account to create; a null flag takes the account default."""
        flags = {
            "is_active": self.is_active,
            "is_staff": self.is_staff,
            "is_superuser": self.is_superuser,
        }
        return NewUser(
            username=self.username,
            email=self.email,
            **{name: value for name, value in flags.items() if value is not None},
        )


class UserAttributesForUpdate(BaseModel):
    """Attributes for update - optional fields"""

    username: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    is_staff: bool | None = None
    is_superuser: bool | None = None

    def to_changes(self) -> UserChanges:
        return UserChanges(
            username=self.username,
            email=self.email,
            is_active=self.is_active,
            is_staff=self.is_staff,
            is_superuser=self.is_superuser,
        )


class UserResource(ResourceObject):
    type: str = Field(default="users", examples=["users"])
    attributes: UserAttributes

    @classmethod
    def from_entity(cls, entity) -> "UserResource":
        """
        Factory method: converts an entity (pydantic User) to UserResource JSON:API.
        Delegates construction to the generic factory in jsonapi.py.
        Excludes sensitive fields like hashed_password.
        """
        return cls.from_model(
            entity,
            type_name="users",
            attributes_field=UserAttributes,
            exclude=["hashed_password"],
        )


class UserResourceForCreation(ResourceObjectForCreation):
    """ResourceObject for user creation (without id)"""

    type: str = Field(default="users", examples=["users"])
    attributes: UserAttributesForCreation


class UserResourceForUpdate(ResourceObjectForCreation):
    """ResourceObject for user update (without id)"""

    type: str = Field(default="users", examples=["users"])
    attributes: UserAttributesForUpdate


class UserCreateRequest(SingleResourceRequest):
    data: UserResourceForCreation


class UserUpdateRequest(SingleResourceRequest):
    data: UserResourceForUpdate


class UserReadResponse(SingleResourceResponse):
    data: UserResource


class UsersCollectionResponse(CollectionResponse):
    data: list[UserResource]
