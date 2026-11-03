from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.app.entities.subscription import Subscription as SubscriptionEntity
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.plan_repository import PlanRepository
from src.app.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)
from src.app.interfaces.http.plan_limits import get_user_plan_limits
from src.app.interfaces.http.presenters.subscription_presenter import (
    SubscriptionPresenter,
)
from src.app.interfaces.http.schemas.subscription_schema import (
    SubscriptionReadResponse,
)
from src.app.security.auth import get_current_active_user
from src.config.logging_config import get_logger

router = APIRouter(tags=["subscriptions"], prefix="/subscriptions")

logger = get_logger(__name__)


def get_subscription_repository(db=Depends(get_db)) -> SubscriptionRepository:
    return SubscriptionRepository(db)


def get_plan_repository(db=Depends(get_db)) -> PlanRepository:
    return PlanRepository(db)


@router.get("/me", response_model=SubscriptionReadResponse)
def get_my_subscription(
    current_user: UserEntity = Depends(get_current_active_user),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
):
    """Get the current user's active subscription (or free plan info)."""
    sub = sub_repo.get_by_user_id(current_user.id)

    if sub:
        plan = plan_repo.get_by_id(sub.plan_id)
        plan_name = plan.display_name if plan else None
        return SubscriptionPresenter.handle_success(sub, plan_name=plan_name)

    # No subscription → synthesize a "free" response
    plan = plan_repo.get_by_name("free")
    free_sub = SubscriptionEntity(
        id=0,
        user_id=current_user.id,
        plan_id=plan.id if plan else 0,
        status="active",
        current_period_start=current_user.created_at or datetime.now(UTC),
        current_period_end=None,
    )
    return SubscriptionPresenter.handle_success(
        free_sub, plan_name=plan.display_name if plan else "Free"
    )


@router.post("/subscribe/{plan_id}", response_model=SubscriptionReadResponse)
def subscribe_to_plan(
    plan_id: int,
    current_user: UserEntity = Depends(get_current_active_user),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
    db: Session = Depends(get_db),
):
    """
    Subscribe the current user to a plan.

    For now this is a simple direct subscription (no payment flow).
    Payment integration (Stripe/Mercado Pago) will be added later.
    """
    plan = plan_repo.get_by_id(plan_id)
    if not plan:
        return SubscriptionPresenter.handle_not_found(f"plan_id={plan_id}")

    if not plan.is_active:
        return SubscriptionPresenter.handle_error(
            400,
            "PLAN_INACTIVE",
            "Plan is not active",
            "This plan is no longer available.",
        )

    # Cancel existing active subscription if any
    existing = sub_repo.get_by_user_id(current_user.id)
    if existing:
        existing.status = "canceled"
        existing.canceled_at = datetime.now(UTC)
        sub_repo.update(existing.id, existing)

    logger.info(
        f"User {current_user.id} subscribing to plan {plan.name}",
        extra={"action": "subscribe", "user_id": current_user.id, "plan_id": plan_id},
    )

    now = datetime.now(UTC)
    new_sub = SubscriptionEntity(
        user_id=current_user.id,
        plan_id=plan_id,
        status="active",
        current_period_start=now,
        current_period_end=None,  # Will be set when payment integration is added
    )
    created = sub_repo.create(new_sub)
    return SubscriptionPresenter.handle_success(created, plan_name=plan.display_name)


@router.post("/cancel", response_model=SubscriptionReadResponse)
def cancel_subscription(
    current_user: UserEntity = Depends(get_current_active_user),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
):
    """Cancel the current user's subscription (reverts to free plan)."""
    sub = sub_repo.get_by_user_id(current_user.id)
    if not sub:
        return SubscriptionPresenter.handle_error(
            400,
            "NO_SUBSCRIPTION",
            "No active subscription",
            "You don't have an active paid subscription to cancel.",
        )

    plan = plan_repo.get_by_id(sub.plan_id)
    if plan and plan.name == "free":
        return SubscriptionPresenter.handle_error(
            400,
            "ALREADY_FREE",
            "Already on free plan",
            "You are already on the free plan.",
        )

    logger.info(
        f"User {current_user.id} canceling subscription {sub.id}",
        extra={"action": "cancel_subscription", "user_id": current_user.id},
    )

    sub.status = "canceled"
    sub.canceled_at = datetime.now(UTC)
    updated = sub_repo.update(sub.id, sub)
    plan_name = plan.display_name if plan else None
    return SubscriptionPresenter.handle_success(updated, plan_name=plan_name)


@router.get("/me/limits")
def get_my_limits(
    limits=Depends(get_user_plan_limits),
):
    """Get the current user's plan limits."""
    return {
        "data": {
            "type": "plan-limits",
            "attributes": {
                "plan_name": limits.plan_name,
                "max_active_alerts": limits.max_active_alerts,
                "min_frequency_minutes": limits.min_frequency_minutes,
                "price_history_days": limits.price_history_days,
                "max_sources": limits.max_sources,
            },
        }
    }
