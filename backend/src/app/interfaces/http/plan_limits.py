"""Plan limits at the HTTP edge.

Loads the data the domain rules need (through repositories) and maps a
PlanLimitViolation to a JSON:API error. The rules themselves are in
src/app/domain/plan_limits.py.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from src.app.domain.plan_limits import (
    PlanLimits,
    PlanLimitViolation,
    alert_limit_violation,
    frequency_limit_violation,
    limits_for_plan,
    source_limit_violation,
)
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.plan_repository import PlanRepository
from src.app.infrastructure.repositories.price_alert_repository import (
    PriceAlertRepository,
)
from src.app.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)
from src.app.security.auth import get_current_active_user
from src.common.jsonapi import JsonApiError


def get_user_plan_limits(
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_active_user),
) -> PlanLimits:
    """FastAPI dependency that returns the current user's plan limits."""
    subscription = SubscriptionRepository(db).get_by_user_id(current_user.id)
    plan = PlanRepository(db).get_by_id(subscription.plan_id) if subscription else None
    return limits_for_plan(plan)


def to_jsonapi_error(violation: PlanLimitViolation | None) -> JsonApiError | None:
    if violation is None:
        return None
    return JsonApiError(
        status="403",
        code="PLAN_LIMIT_REACHED",
        title=violation.title,
        detail=violation.detail,
        source={"pointer": violation.pointer} if violation.pointer else None,
        meta=violation.meta,
    )


def check_alert_limit(
    db: Session, user_id: int, limits: PlanLimits
) -> JsonApiError | None:
    """Check if user can create a new active alert."""
    active_count = PriceAlertRepository(db).count_active_by_user_id(user_id)
    return to_jsonapi_error(alert_limit_violation(active_count, limits))


def check_frequency_limit(
    frequency_minutes: int, limits: PlanLimits
) -> JsonApiError | None:
    """Check if the requested frequency is allowed by the user's plan."""
    return to_jsonapi_error(frequency_limit_violation(frequency_minutes, limits))


def check_source_limit(source_count: int, limits: PlanLimits) -> JsonApiError | None:
    """Check if the number of sources is allowed by the user's plan."""
    return to_jsonapi_error(source_limit_violation(source_count, limits))
