"""The logged-in user's plan limits, as a FastAPI dependency."""

from fastapi import Depends
from sqlalchemy.orm import Session

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import get_current_active_user
from src.app.billing import wiring
from src.app.billing.limits import PlanLimits
from src.app.infrastructure.database_config import get_db


def get_user_plan_limits(
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_active_user),
) -> PlanLimits:
    """FastAPI dependency that returns the current user's plan limits."""
    return wiring.user_plan_limits(db).execute(current_user.id)
