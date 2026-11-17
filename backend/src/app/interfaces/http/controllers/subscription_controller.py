from fastapi import APIRouter, Depends

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import get_current_active_user
from src.app.billing.http.limits import get_user_plan_limits
from src.app.billing.persistence.repositories import (
    PlanRepository,
    SubscriptionRepository,
)
from src.app.billing.use_cases import (
    AlreadyFreeError,
    CancelSubscriptionUseCase,
    GetMySubscriptionUseCase,
    MySubscription,
    NoSubscriptionError,
    PlanInactiveError,
    PlanNotFoundError,
    SubscribeUseCase,
)
from src.app.infrastructure.database_config import get_db
from src.app.interfaces.http.presenters.subscription_presenter import (
    SubscriptionPresenter,
)
from src.app.interfaces.http.schemas.subscription_schema import (
    SubscriptionReadResponse,
)

router = APIRouter(tags=["subscriptions"], prefix="/subscriptions")


def get_subscription_repository(db=Depends(get_db)) -> SubscriptionRepository:
    return SubscriptionRepository(db)


def get_plan_repository(db=Depends(get_db)) -> PlanRepository:
    return PlanRepository(db)


def _present(mine: MySubscription) -> SubscriptionReadResponse:
    return SubscriptionPresenter.handle_success(
        mine.subscription, plan_name=mine.plan_name
    )


@router.get("/me", response_model=SubscriptionReadResponse)
def get_my_subscription(
    current_user: UserEntity = Depends(get_current_active_user),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
):
    """Get the current user's active subscription (or free plan info)."""
    mine = GetMySubscriptionUseCase(plan_repo, sub_repo).execute(
        current_user.id, member_since=current_user.created_at
    )
    return _present(mine)


@router.post("/subscribe/{plan_id}", response_model=SubscriptionReadResponse)
def subscribe_to_plan(
    plan_id: int,
    current_user: UserEntity = Depends(get_current_active_user),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
):
    """
    Subscribe the current user to a plan.

    For now this is a simple direct subscription (no payment flow).
    Payment integration (Stripe/Mercado Pago) will be added later.
    """
    try:
        mine = SubscribeUseCase(plan_repo, sub_repo).execute(current_user.id, plan_id)
    except PlanNotFoundError:
        return SubscriptionPresenter.handle_not_found(f"plan_id={plan_id}")
    except PlanInactiveError:
        return SubscriptionPresenter.handle_error(
            400,
            "PLAN_INACTIVE",
            "Plan is not active",
            "This plan is no longer available.",
        )
    return _present(mine)


@router.post("/cancel", response_model=SubscriptionReadResponse)
def cancel_subscription(
    current_user: UserEntity = Depends(get_current_active_user),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
    plan_repo: PlanRepository = Depends(get_plan_repository),
):
    """Cancel the current user's subscription (reverts to free plan)."""
    try:
        mine = CancelSubscriptionUseCase(plan_repo, sub_repo).execute(current_user.id)
    except NoSubscriptionError:
        return SubscriptionPresenter.handle_error(
            400,
            "NO_SUBSCRIPTION",
            "No active subscription",
            "You don't have an active paid subscription to cancel.",
        )
    except AlreadyFreeError:
        return SubscriptionPresenter.handle_error(
            400,
            "ALREADY_FREE",
            "Already on free plan",
            "You are already on the free plan.",
        )
    return _present(mine)


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
