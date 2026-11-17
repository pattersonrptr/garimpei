from fastapi.responses import JSONResponse

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.user_schema import UserReadResponse, UserResource
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse


class UserPresenter:
    """
    Presenter for User entities following Clean Architecture.
    Transforms domain entities into HTTP presentation formats (JSON:API).
    """

    @staticmethod
    def handle_validation_errors(validation_errors: list) -> JSONResponse:
        """
        Returns validation errors in JSON:API format.
        """
        first_error = validation_errors[0]
        status_code = int(first_error.status)
        return JSONResponse(
            status_code=status_code,
            content=JsonApiErrorResponse(errors=validation_errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_not_found(identifier: str, pointer: str) -> JSONResponse:
        """
        Returns 404 in JSON:API format.
        """
        errors = [
            JsonApiError(
                status="404",
                code="NOT_FOUND",
                title="User not found",
                detail=f"User with {identifier} not found",
                source={"pointer": pointer},
            )
        ]
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    @staticmethod
    def handle_success(entity: UserEntity) -> UserReadResponse:
        """
        Returns user in JSON:API format (success).
        """
        return UserReadResponse(data=UserResource.from_entity(entity))
