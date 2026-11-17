from pydantic import BaseModel, Field

from src.common.jsonapi import (
    ResourceObject,
    ResourceObjectForCreation,
    SingleResourceRequest,
    SingleResourceResponse,
)


class TokenPayload(BaseModel):
    token: str


class TokenAttributes(BaseModel):
    """Attributes for token response"""

    access_token: str
    token_type: str
    expires_in: int  # minutes


class TokenResource(ResourceObject):
    """JSON:API resource for authentication tokens"""

    type: str = Field(default="auth", examples=["auth"])
    attributes: TokenAttributes

    @classmethod
    def from_values(
        cls, access_token: str, token_type: str, expires_in: int
    ) -> "TokenResource":
        """
        Factory method: creates TokenResource from token values.
        Delegates construction to the generic factory in jsonapi.py.
        """
        token_model = TokenAttributes(
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
        )
        return cls.from_model(
            token_model,
            type_name="auth",
            attributes_field=TokenAttributes,
        )


class TokenResponse(SingleResourceResponse):
    """JSON:API response for token endpoints"""

    data: TokenResource
    meta: dict | None = None


class TokenValidationAttributes(BaseModel):
    """Attributes for token validation response"""

    is_valid: bool
    message: str | None = None


class TokenValidationResource(ResourceObject):
    """JSON:API resource for token validation"""

    type: str = Field(default="token-validations", examples=["token-validations"])
    attributes: TokenValidationAttributes

    @classmethod
    def from_values(
        cls, is_valid: bool, message: str | None = None
    ) -> "TokenValidationResource":
        """
        Factory method: creates TokenValidationResource from validation values.
        Delegates construction to the generic factory in jsonapi.py.
        """
        validation_model = TokenValidationAttributes(
            is_valid=is_valid,
            message=message,
        )
        return cls.from_model(
            validation_model,
            type_name="token-validations",
            attributes_field=TokenValidationAttributes,
        )


class TokenValidationResponse(SingleResourceResponse):
    """JSON:API response for token validation"""

    data: TokenValidationResource


class TokenValidationRequestAttributes(BaseModel):
    """Attributes for token validation request"""

    token: str


class TokenValidationRequestResource(ResourceObjectForCreation):
    """JSON:API resource for token validation request (without id)"""

    type: str = Field(default="token-validations", examples=["token-validations"])
    attributes: TokenValidationRequestAttributes


class TokenValidationRequest(SingleResourceRequest):
    """JSON:API request for token validation endpoint"""

    data: TokenValidationRequestResource


MIN_PASSWORD_LENGTH = 8


class PasswordChangeAttributes(BaseModel):
    """Change one's own password: the current one proves it is the owner."""

    current_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class PasswordChangeResource(ResourceObjectForCreation):
    type: str = Field(default="password_change", examples=["password_change"])
    attributes: PasswordChangeAttributes


class PasswordChangeRequest(SingleResourceRequest):
    data: PasswordChangeResource
