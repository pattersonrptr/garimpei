"""Builds billing's repositories and the use cases other modules read.

Billing's controllers and the plan-limits dependency get the repositories
here, and alerts reads a user's limits through ``user_plan_limits``, so
none of them builds the SQLAlchemy repositories itself.
"""

from sqlalchemy.orm import Session

from src.app.billing.persistence.repositories import (
    PlanRepository,
    SubscriptionRepository,
)
from src.app.billing.ports import (
    PlanRepositoryInterface,
    SubscriptionRepositoryInterface,
)
from src.app.billing.use_cases import GetUserPlanLimitsUseCase


def plans(db: Session) -> PlanRepositoryInterface:
    return PlanRepository(db)


def subscriptions(db: Session) -> SubscriptionRepositoryInterface:
    return SubscriptionRepository(db)


def user_plan_limits(db: Session) -> GetUserPlanLimitsUseCase:
    """Answers what a user's plan allows; what other modules need from billing."""
    return GetUserPlanLimitsUseCase(plans(db), subscriptions(db))
