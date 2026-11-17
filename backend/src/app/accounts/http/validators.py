from src.app.accounts.http.user_schema import (
    UserCreateRequest,
    UserUpdateRequest,
)
from src.app.accounts.ports import UserRepositoryInterface
from src.common.jsonapi import JsonApiError


class UserValidator:
    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def validate_create_request(self, user_in: UserCreateRequest) -> list[JsonApiError]:
        """
        Validates a user creation request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "users"
        if user_in.data.type != "users":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'users', got '{user_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = user_in.data.attributes

        # Validation 2: username required
        if not attrs.username or not attrs.username.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'username' is required",
                    source={"pointer": "/data/attributes/username"},
                )
            )

        # Validation 3: email required
        if not attrs.email or not attrs.email.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'email' is required",
                    source={"pointer": "/data/attributes/email"},
                )
            )

        # Validation 4: password required
        if not attrs.password or not attrs.password.strip():
            errors.append(
                JsonApiError(
                    status="422",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'password' is required",
                    source={"pointer": "/data/attributes/password"},
                )
            )

        # If there are required field errors, return early (don't validate duplicates)
        if errors:
            return errors

        # Validation 5: username already exists
        existing_user_username = self.user_repo.get_by_username(attrs.username)
        if existing_user_username:
            errors.append(
                JsonApiError(
                    status="409",
                    code="DUPLICATE_USERNAME",
                    title="Conflict",
                    detail=f"Username '{attrs.username}' is already registered",
                    source={"pointer": "/data/attributes/username"},
                )
            )

        # Validation 6: email already exists
        existing_user_email = self.user_repo.get_by_email(attrs.email)
        if existing_user_email:
            errors.append(
                JsonApiError(
                    status="409",
                    code="DUPLICATE_EMAIL",
                    title="Conflict",
                    detail=f"Email '{attrs.email}' is already registered",
                    source={"pointer": "/data/attributes/email"},
                )
            )

        return errors

    def validate_update_request(
        self, user_in: UserUpdateRequest, user_id: int
    ) -> list[JsonApiError]:
        """
        Validates a user update request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation 1: type must be "users"
        if user_in.data.type != "users":
            errors.append(
                JsonApiError(
                    status="400",
                    code="INVALID_TYPE",
                    title="Invalid resource type",
                    detail=f"Expected type 'users', got '{user_in.data.type}'",
                    source={"pointer": "/data/type"},
                )
            )

        attrs = user_in.data.attributes

        # Validation 2: at least one field must be provided
        if not any([attrs.username, attrs.email, attrs.is_active is not None]):
            errors.append(
                JsonApiError(
                    status="422",
                    code="EMPTY_UPDATE",
                    title="Validation error",
                    detail="At least one field must be provided for update",
                    source={"pointer": "/data/attributes"},
                )
            )
            return errors

        # Validation 3: username already exists (if provided and different from current)
        if attrs.username:
            existing_user = self.user_repo.get_by_username(attrs.username)
            if existing_user and existing_user.id != user_id:
                errors.append(
                    JsonApiError(
                        status="409",
                        code="DUPLICATE_USERNAME",
                        title="Conflict",
                        detail=f"Username '{attrs.username}' is already registered",
                        source={"pointer": "/data/attributes/username"},
                    )
                )

        # Validation 4: email already exists (if provided and different from current)
        if attrs.email:
            existing_user = self.user_repo.get_by_email(attrs.email)
            if existing_user and existing_user.id != user_id:
                errors.append(
                    JsonApiError(
                        status="409",
                        code="DUPLICATE_EMAIL",
                        title="Conflict",
                        detail=f"Email '{attrs.email}' is already registered",
                        source={"pointer": "/data/attributes/email"},
                    )
                )

        return errors

    def validate_delete_request(self, user_id: int) -> list[JsonApiError]:
        """
        Validates a user deletion request.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation: user exists
        existing_user = self.user_repo.get_by_id(user_id)
        if not existing_user:
            errors.append(
                JsonApiError(
                    status="404",
                    code="NOT_FOUND",
                    title="User not found",
                    detail=f"User with id {user_id} not found",
                    source={"pointer": "/data/id"},
                )
            )

        return errors

    def validate_get_by_username_request(self, username: str) -> list[JsonApiError]:
        """
        Validates a search request by username.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation: username provided
        if not username or not username.strip():
            errors.append(
                JsonApiError(
                    status="400",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'username' is required",
                    source={"pointer": "/username"},
                )
            )

        return errors

    def validate_get_by_email_request(self, email: str) -> list[JsonApiError]:
        """
        Validates a search request by email.
        Returns list of errors (empty if valid).
        """
        errors = []

        # Validation: email provided
        if not email or not email.strip():
            errors.append(
                JsonApiError(
                    status="400",
                    code="MISSING_FIELD",
                    title="Validation error",
                    detail="Field 'email' is required",
                    source={"pointer": "/email"},
                )
            )

        return errors
