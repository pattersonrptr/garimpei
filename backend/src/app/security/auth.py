from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.user_repository import UserRepository
from src.config import settings

reusable_oauth2 = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(reusable_oauth2),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=401, detail="Could not validate credentials"
            )
    except JWTError as err:
        raise HTTPException(
            status_code=401, detail="Could not validate credentials"
        ) from err
    user_repo = UserRepository(db)
    user = user_repo.get_by_username(username=username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_current_active_user(current_user=Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_staff_user(current_user=Depends(get_current_active_user)):
    """
    Requires user to be staff or superuser.
    Use for endpoints that need elevated permissions.
    """
    if not current_user.is_staff and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this resource. Staff access required.",
        )
    return current_user


async def get_current_superuser(current_user=Depends(get_current_active_user)):
    """
    Requires user to be superuser.
    Use for sensitive operations like creating users, deleting users, etc.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this resource. Superuser access required.",
        )
    return current_user


def is_staff_or_superuser(user) -> bool:
    """True for users allowed to see and manage every user's resources."""
    return bool(user.is_staff or user.is_superuser)


def can_access_owned_resource(owner_id: int | None, user) -> bool:
    """
    Ownership rule for per-user resources (price alerts, search configs).

    Staff and superusers can access any resource; regular users only their own.
    Controllers answer 404 (not 403) when this is False, so a regular user
    can't probe which IDs exist.
    """
    return is_staff_or_superuser(user) or owner_id == user.id
