"""Builds billing use cases from a database session.

Other modules call these factories, so they never see billing's
repositories.
"""

from sqlalchemy.orm import Session

from src.app.billing.persistence.repositories import (
    PlanRepository,
    SubscriptionRepository,
)
from src.app.billing.use_cases import GetUserPlanLimitsUseCase


def user_plan_limits(db: Session) -> GetUserPlanLimitsUseCase:
    """Answers what a user's plan allows."""
    return GetUserPlanLimitsUseCase(PlanRepository(db), SubscriptionRepository(db))
