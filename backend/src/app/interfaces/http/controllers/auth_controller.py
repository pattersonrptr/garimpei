from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.user_repository import UserRepository
from src.app.interfaces.http.presenters.auth_presenter import AuthPresenter
from src.app.interfaces.http.presenters.user_presenter import UserPresenter
from src.app.interfaces.http.schemas.auth_schema import (
    PasswordChangeRequest,
    TokenResponse,
    TokenValidationRequest,
    TokenValidationResponse,
)
from src.app.interfaces.http.schemas.user_schema import (
    UserCreateRequest,
    UserReadResponse,
)
from src.app.security.auth import get_current_active_user
from src.app.use_cases.user_use_cases import (
    CreateUserUseCase,
    GetUserByEmailUseCase,
    GetUserByUsernameUseCase,
    pwd_context,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse
from src.config import settings
from src.config.logging_config import get_logger

auth_router = APIRouter(tags=["auth"], prefix="/auth")
logger = get_logger(__name__)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Authenticate user and return JWT token in JSON:API format.

    The ``username`` field takes a username or an e-mail address (a value
    with "@" is looked up as an e-mail).

    Returns:
        TokenResponse: JSON:API formatted token response with user metadata
    """
    logger.info(f"Login attempt for username: {form_data.username}")

    login_name = form_data.username.strip()
    if "@" in login_name:
        user = GetUserByEmailUseCase(user_repo).execute(login_name)
    else:
        user = GetUserByUsernameUseCase(user_repo).execute(login_name)

    if not user:
        logger.warning(
            f"Login failed: User not found - {form_data.username}",
            extra={"username": form_data.username, "reason": "user_not_found"},
        )
        return AuthPresenter.handle_invalid_credentials()

    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(
            f"Login failed: Invalid password for user - {form_data.username}",
            extra={
                "username": form_data.username,
                "user_id": user.id,
                "reason": "invalid_password",
            },
        )
        return AuthPresenter.handle_invalid_credentials()

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
        expires_delta=access_token_expires,
    )

    logger.info(
        f"Login successful for user: {user.username} (ID: {user.id})",
        extra={
            "action": "login_success",
            "user_id": user.id,
            "username": user.username,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
    )

    return AuthPresenter.present_token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        meta={
            "user_id": user.id,
            "username": user.username,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
    )


@auth_router.post("/verify-token", response_model=TokenValidationResponse)
async def verify_token(request: TokenValidationRequest):
    """
    Verify if a JWT token is valid.

    Request body (JSON:API):
        {
            "data": {
                "type": "token-validations",
                "attributes": {
                    "token": "your-jwt-token-here"
                }
            }
        }

    Returns:
        TokenValidationResponse: JSON:API formatted validation result
    """
    token = request.data.attributes.token

    try:
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug("Token verification successful")
        return AuthPresenter.present_token_validation(
            is_valid=True, message="Token is valid"
        )
    except JWTError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        return AuthPresenter.present_token_validation(
            is_valid=False, message=f"Token verification failed: {str(e)}"
        )


@auth_router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(current_user: UserEntity = Depends(get_current_active_user)):
    """
    Refresh an existing JWT token.

    Returns:
        TokenResponse: JSON:API formatted token response
    """
    logger.info(
        f"Token refresh for user: {current_user.username} (ID: {current_user.id})",
        extra={"action": "refresh_token", "user_id": current_user.id},
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={
            "sub": current_user.username,
            "user_id": current_user.id,
            "email": current_user.email,
            "is_staff": current_user.is_staff,
            "is_superuser": current_user.is_superuser,
        },
        expires_delta=access_token_expires,
    )

    return AuthPresenter.present_token(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        meta={
            "user_id": current_user.id,
            "username": current_user.username,
        },
    )


@auth_router.post("/register", response_model=UserReadResponse, status_code=201)
async def register(
    user_in: UserCreateRequest,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Public user registration endpoint.

    Creates a new regular user account (is_staff=False, is_superuser=False).
    No authentication required — any visitor can sign up.

    Returns:
        UserReadResponse: JSON:API formatted user resource (without sensitive fields)
    """
    logger.info(
        f"Registration attempt for username: {user_in.data.attributes.username}",
        extra={"username": user_in.data.attributes.username},
    )

    # Reject attempts to self-assign elevated privileges
    user_in.data.attributes.is_staff = False
    user_in.data.attributes.is_superuser = False

    # Check for duplicate username
    existing_username = GetUserByUsernameUseCase(user_repo).execute(
        user_in.data.attributes.username
    )
    if existing_username:
        errors = [
            JsonApiError(
                status="409",
                code="USERNAME_TAKEN",
                title="Username Already Taken",
                detail=f"Username '{user_in.data.attributes.username}' is already registered.",
                source={"pointer": "/data/attributes/username"},
            )
        ]
        return JSONResponse(
            status_code=409,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    # Check for duplicate email
    existing_email = GetUserByEmailUseCase(user_repo).execute(
        user_in.data.attributes.email
    )
    if existing_email:
        errors = [
            JsonApiError(
                status="409",
                code="EMAIL_TAKEN",
                title="Email Already Registered",
                detail=f"Email '{user_in.data.attributes.email}' is already registered.",
                source={"pointer": "/data/attributes/email"},
            )
        ]
        return JSONResponse(
            status_code=409,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    hashed_password = pwd_context.hash(user_in.data.attributes.password)
    use_case = CreateUserUseCase(user_repo)
    created_user = use_case.execute(user_in, hashed_password)

    logger.info(
        f"User registered successfully: {created_user.username} (ID: {created_user.id})",
        extra={"action": "user_registered", "user_id": created_user.id},
    )

    return UserPresenter.handle_success(created_user)


@auth_router.get("/me", response_model=UserReadResponse)
async def me(current_user: UserEntity = Depends(get_current_active_user)):
    """The logged-in user's own account (no sensitive fields)."""
    return UserPresenter.handle_success(current_user)


@auth_router.put("/password", status_code=204)
async def change_password(
    password_in: PasswordChangeRequest,
    current_user: UserEntity = Depends(get_current_active_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Change the logged-in user's password.

    Returns:
        - 204: changed
        - 400: the current password is wrong
        - 422: the new password is shorter than 8 characters
    """
    attrs = password_in.data.attributes
    user = user_repo.get_by_id(current_user.id)
    if user is None or not verify_password(
        attrs.current_password, user.hashed_password or ""
    ):
        logger.warning(
            "Password change refused: wrong current password",
            extra={"action": "password_change_refused", "user_id": current_user.id},
        )
        errors = [
            JsonApiError(
                status="400",
                code="WRONG_PASSWORD",
                title="Wrong password",
                detail="The current password is not correct.",
                source={"pointer": "/data/attributes/current_password"},
            )
        ]
        return JSONResponse(
            status_code=400,
            content=JsonApiErrorResponse(errors=errors).model_dump(),
            media_type="application/vnd.api+json",
        )

    user_repo.update(
        user.id,
        user.model_copy(
            update={"hashed_password": pwd_context.hash(attrs.new_password)}
        ),
    )
    logger.info(
        "Password changed",
        extra={"action": "password_changed", "user_id": current_user.id},
    )
    return Response(status_code=204)
