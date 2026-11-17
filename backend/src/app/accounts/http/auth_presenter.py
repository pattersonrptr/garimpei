from fastapi.responses import JSONResponse

from src.app.accounts.http.auth_schema import (
    TokenResource,
    TokenResponse,
    TokenValidationResource,
    TokenValidationResponse,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class AuthPresenter:
    """
    Presenter for Authentication following Clean Architecture.
    Transforms authentication data into HTTP presentation formats (JSON:API).
    """

    @staticmethod
    def present_token(
        access_token: str,
        token_type: str = "bearer",
        expires_in: int = 1440,
        meta: dict | None = None,
    ) -> TokenResponse:
        """
        Returns authentication token in JSON:API format.

        Args:
            access_token: JWT token string
            token_type: Type of token (default: "bearer")
            expires_in: Token expiration time in minutes
            meta: Optional metadata (e.g., user_id, username)
        """
        token_resource = TokenResource.from_values(
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
        )

        return TokenResponse(
            data=token_resource,
            meta=meta,
        )

    @staticmethod
    def present_token_validation(
        is_valid: bool, message: str | None = None
    ) -> TokenValidationResponse:
        """
        Returns token validation result in JSON:API format.

        Args:
            is_valid: Whether the token is valid
            message: Optional message (e.g., error reason)
        """
        validation_resource = TokenValidationResource.from_values(
            is_valid=is_valid,
            message=message,
        )

        return TokenValidationResponse(data=validation_resource)

    @staticmethod
    def handle_authentication_error(detail: str) -> JSONResponse:
        """
        Returns authentication error in JSON:API format.

        Args:
            detail: Error message
        """
        errors = [
            JsonApiError(
                status="401",
                code="AUTHENTICATION_FAILED",
                title="Authentication Failed",
                detail=detail,
                source={"pointer": "/data/attributes/credentials"},
            )
        ]
        return JSONResponse(
            status_code=401,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_invalid_credentials() -> JSONResponse:
        """
        Returns invalid credentials error in JSON:API format.
        """
        errors = [
            JsonApiError(
                status="400",
                code="INVALID_CREDENTIALS",
                title="Invalid Credentials",
                detail="Incorrect username or password",
                source={"pointer": "/data/attributes/credentials"},
            )
        ]
        return JSONResponse(
            status_code=400,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )
