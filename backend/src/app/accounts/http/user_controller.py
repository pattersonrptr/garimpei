from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.app.accounts import wiring
from src.app.accounts.adapters.passwords import pwd_context
from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import get_current_staff_user, get_current_superuser
from src.app.accounts.http.user_presenter import UserPresenter
from src.app.accounts.http.user_schema import (
    UserCreateRequest,
    UserReadResponse,
    UserResource,
    UsersCollectionResponse,
    UserUpdateRequest,
)
from src.app.accounts.http.validators import UserValidator
from src.app.accounts.ports import UserRepositoryInterface
from src.app.accounts.use_cases import (
    CreateUserUseCase,
    DeleteUserUseCase,
    GetAllUsersUseCase,
    GetUserByEmailUseCase,
    GetUserByIdUseCase,
    GetUserByUsernameUseCase,
    UpdateUserUseCase,
)
from src.app.infrastructure.database_config import get_db
from src.common.jsonapi import JsonApiErrorResponse
from src.config.logging_config import get_logger

router = APIRouter(tags=["users"], prefix="/users")

logger = get_logger(__name__)


def get_user_repository(db=Depends(get_db)) -> UserRepositoryInterface:
    return wiring.users(db)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


@router.post("/", response_model=UserReadResponse, status_code=201)
def create_user(
    user_in: UserCreateRequest,
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
    current_user: UserEntity = Depends(get_current_superuser),
):
    """
    Create a new user. Only superusers can create users.
    This prevents unauthorized user registration.
    """
    logger.info(
        f"Creating new user: {user_in.data.attributes.username}",
        extra={"action": "create_user", "admin_user_id": current_user.id},
    )

    validator = UserValidator(user_repo)
    validation_errors = validator.validate_create_request(user_in)

    if validation_errors:
        logger.warning(
            f"User creation validation failed for {user_in.data.attributes.username}",
            extra={"errors": len(validation_errors)},
        )
        return UserPresenter.handle_validation_errors(validation_errors)

    attrs = user_in.data.attributes
    hashed_password = hash_password(attrs.password)
    use_case = CreateUserUseCase(user_repo)
    created_user = use_case.execute(attrs.to_new_user(), hashed_password)

    logger.info(
        f"User created successfully: {created_user.username} (ID: {created_user.id})",
        extra={
            "action": "user_created",
            "user_id": created_user.id,
            "username": created_user.username,
            "admin_user_id": current_user.id,
        },
    )

    return UserPresenter.handle_success(created_user)


@router.get("/", response_model=UsersCollectionResponse)
def read_users(
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    List all users. Requires staff or superuser access.
    """
    get_all_users_uc = GetAllUsersUseCase(user_repo)
    users_entities = get_all_users_uc.execute()
    data = [UserResource.from_entity(u) for u in users_entities]
    return {"data": data}


@router.get("/username/{username}", response_model=UserReadResponse)
def read_user_by_username(
    username: str,
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Returns a user by username in JSON:API format.
    Requires staff or superuser access.
    - 200: { "data": { ...resource object... } }
    - 400: { "errors": [ validation ] }
    - 403: { "errors": [ permission denied ] }
    - 404: { "errors": [ { status, code, title, detail, source } ] }
    """
    validator = UserValidator(user_repo)
    validation_errors = validator.validate_get_by_username_request(username)

    if validation_errors:
        return UserPresenter.handle_validation_errors(validation_errors)

    get_user_uc = GetUserByUsernameUseCase(user_repo)
    user_entity = get_user_uc.execute(username)

    if not user_entity:
        return UserPresenter.handle_not_found(f"username '{username}'", "/username")

    return UserPresenter.handle_success(user_entity)


@router.get("/email/{email}", response_model=UserReadResponse)
def read_user_by_email(
    email: str,
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Returns a user by email in JSON:API format.
    Requires staff or superuser access.
    - 200: { "data": { ...resource object... } }
    - 400: { "errors": [ validation ] }
    - 403: { "errors": [ permission denied ] }
    - 404: { "errors": [ { status, code, title, detail, source } ] }
    """
    validator = UserValidator(user_repo)
    validation_errors = validator.validate_get_by_email_request(email)

    if validation_errors:
        return UserPresenter.handle_validation_errors(validation_errors)

    get_user_uc = GetUserByEmailUseCase(user_repo)
    user_entity = get_user_uc.execute(email)

    if not user_entity:
        return UserPresenter.handle_not_found(f"email '{email}'", "/email")

    return UserPresenter.handle_success(user_entity)


@router.get("/{user_id}", response_model=UserReadResponse)
def read_user(
    user_id: int,
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Returns a single user in JSON:API format.
    Requires staff or superuser access.
    - 200: { "data": { ...resource object... } }
    - 403: { "errors": [ permission denied ] }
    - 404: { "errors": [ { status, code, title, detail, source } ] }
    """
    get_user_uc = GetUserByIdUseCase(user_repo)
    user_entity = get_user_uc.execute(user_id)

    if not user_entity:
        return UserPresenter.handle_not_found(f"id {user_id}", "/data/id")

    return UserPresenter.handle_success(user_entity)


@router.put("/{user_id}", response_model=UserReadResponse)
def update_user(
    user_id: int,
    user_in: UserUpdateRequest,
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
    current_user: UserEntity = Depends(get_current_superuser),
):
    """
    Updates a user in JSON:API format.
    Only superusers can update users (including permissions).
    - 200: { "data": { ...resource object... } }
    - 403: { "errors": [ permission denied ] }
    - 404: { "errors": [ { status, code, title, detail, source } ] }
    - 409: { "errors": [ duplicate username/email conflict ] }
    - 422: { "errors": [ validation ] }
    """
    logger.info(
        f"Updating user ID: {user_id}",
        extra={
            "action": "update_user",
            "target_user_id": user_id,
            "admin_user_id": current_user.id,
        },
    )

    validator = UserValidator(user_repo)
    validation_errors = validator.validate_update_request(user_in, user_id)

    if validation_errors:
        logger.warning(
            f"User update validation failed for ID: {user_id}",
            extra={"errors": len(validation_errors)},
        )
        return UserPresenter.handle_validation_errors(validation_errors)

    get_user_uc = GetUserByIdUseCase(user_repo)
    user_entity = get_user_uc.execute(user_id)

    if not user_entity:
        logger.warning(f"User not found for update: ID {user_id}")
        return UserPresenter.handle_not_found(f"id {user_id}", "/data/id")

    update_uc = UpdateUserUseCase(user_repo)
    updated_user = update_uc.execute(user_id, user_in.data.attributes.to_changes())

    logger.info(
        f"User updated successfully: {updated_user.username} (ID: {user_id})",
        extra={
            "action": "user_updated",
            "user_id": user_id,
            "username": updated_user.username,
            "admin_user_id": current_user.id,
        },
    )

    return UserPresenter.handle_success(updated_user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
    current_user: UserEntity = Depends(get_current_superuser),
):
    """
    Deletes a user in JSON:API format.
    Only superusers can delete users.
    - 204: No Content (success, no body)
    - 403: { "errors": [ permission denied ] }
    - 404: { "errors": [ { status, code, title, detail, source } ] }
    """
    logger.warning(
        f"Deleting user ID: {user_id}",
        extra={
            "action": "delete_user",
            "target_user_id": user_id,
            "admin_user_id": current_user.id,
        },
    )

    validator = UserValidator(user_repo)
    validation_errors = validator.validate_delete_request(user_id)

    if validation_errors:
        return JSONResponse(
            status_code=404,
            content=JsonApiErrorResponse(errors=validation_errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    get_user_uc = GetUserByIdUseCase(user_repo)
    user_entity = get_user_uc.execute(user_id)

    if not user_entity:
        logger.warning(f"User not found for deletion: ID {user_id}")
        return UserPresenter.handle_not_found(f"id {user_id}", "/data/id")

    delete_uc = DeleteUserUseCase(user_repo)
    deleted = delete_uc.execute(user_id)

    if not deleted:
        logger.error(f"Failed to delete user ID: {user_id}")
        return UserPresenter.handle_not_found(f"id {user_id}", "/data/id")

    logger.warning(
        f"User deleted successfully: {user_entity.username} (ID: {user_id})",
        extra={
            "action": "user_deleted",
            "user_id": user_id,
            "username": user_entity.username,
            "admin_user_id": current_user.id,
        },
    )

    return None
