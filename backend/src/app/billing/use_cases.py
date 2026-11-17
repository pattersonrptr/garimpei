"""Billing use cases: plans and the user's subscription.

They take and return plain data (entities, ids, dates); a refusal is a
domain error that the HTTP layer maps to an API error.
"""

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from src.app.billing.entities import Plan, Subscription
from src.app.billing.limits import PlanLimits, limits_for_plan
from src.app.billing.ports import (
    PlanRepositoryInterface,
    SubscriptionRepositoryInterface,
)
from src.config.logging_config import get_logger

logger = get_logger(__name__)

FREE_PLAN_NAME = "free"


class PlanNotFoundError(Exception):
    """No plan has this id."""


class PlanInactiveError(Exception):
    """The plan is no longer offered."""


class NoSubscriptionError(Exception):
    """The user has no active subscription to cancel."""


class AlreadyFreeError(Exception):
    """The user is on the free plan, which cannot be canceled."""


@dataclass(frozen=True)
class MySubscription:
    """A subscription and the display name of its plan (None if the plan
    no longer exists)."""

    subscription: Subscription
    plan_name: str | None


class ListPlansUseCase:
    def __init__(self, plans: PlanRepositoryInterface):
        self.plans = plans

    def execute(self) -> list[Plan]:
        """The plans on offer, cheapest first."""
        return self.plans.get_all()


class GetPlanUseCase:
    def __init__(self, plans: PlanRepositoryInterface):
        self.plans = plans

    def execute(self, plan_id: int) -> Plan:
        plan = self.plans.get_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError(plan_id)
        return plan


class CreatePlanUseCase:
    def __init__(self, plans: PlanRepositoryInterface):
        self.plans = plans

    def execute(self, plan: Plan) -> Plan:
        return self.plans.create(plan)


class GetMySubscriptionUseCase:
    def __init__(
        self,
        plans: PlanRepositoryInterface,
        subscriptions: SubscriptionRepositoryInterface,
    ):
        self.plans = plans
        self.subscriptions = subscriptions

    def execute(self, user_id: int, member_since: datetime | None) -> MySubscription:
        """The user's active subscription, or the free plan since they joined."""
        subscription = self.subscriptions.get_by_user_id(user_id)
        if subscription:
            plan = self.plans.get_by_id(subscription.plan_id)
            return MySubscription(subscription, plan.display_name if plan else None)

        free = self.plans.get_by_name(FREE_PLAN_NAME)
        synthesized = Subscription(
            id=0,
            user_id=user_id,
            plan_id=free.id if free and free.id is not None else 0,
            status="active",
            current_period_start=member_since or datetime.now(UTC),
            current_period_end=None,
        )
        return MySubscription(synthesized, free.display_name if free else "Free")


class SubscribeUseCase:
    """Direct subscription, no payment flow yet."""

    def __init__(
        self,
        plans: PlanRepositoryInterface,
        subscriptions: SubscriptionRepositoryInterface,
    ):
        self.plans = plans
        self.subscriptions = subscriptions

    def execute(self, user_id: int, plan_id: int) -> MySubscription:
        plan = self.plans.get_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError(plan_id)
        if not plan.is_active:
            raise PlanInactiveError(plan_id)

        current = self.subscriptions.get_by_user_id(user_id)
        if current and current.id is not None:
            self.subscriptions.update(
                current.id,
                replace(current, status="canceled", canceled_at=datetime.now(UTC)),
            )

        logger.info(
            f"User {user_id} subscribing to plan {plan.name}",
            extra={"action": "subscribe", "user_id": user_id, "plan_id": plan_id},
        )
        created = self.subscriptions.create(
            Subscription(
                user_id=user_id,
                plan_id=plan_id,
                status="active",
                current_period_start=datetime.now(UTC),
                current_period_end=None,  # set when payments arrive
            )
        )
        return MySubscription(created, plan.display_name)


class CancelSubscriptionUseCase:
    """Cancels the paid subscription; the user goes back to the free plan."""

    def __init__(
        self,
        plans: PlanRepositoryInterface,
        subscriptions: SubscriptionRepositoryInterface,
    ):
        self.plans = plans
        self.subscriptions = subscriptions

    def execute(self, user_id: int) -> MySubscription:
        subscription = self.subscriptions.get_by_user_id(user_id)
        if subscription is None or subscription.id is None:
            raise NoSubscriptionError(user_id)

        plan = self.plans.get_by_id(subscription.plan_id)
        if plan and plan.name == FREE_PLAN_NAME:
            raise AlreadyFreeError(user_id)

        logger.info(
            f"User {user_id} canceling subscription {subscription.id}",
            extra={"action": "cancel_subscription", "user_id": user_id},
        )
        updated = self.subscriptions.update(
            subscription.id,
            replace(subscription, status="canceled", canceled_at=datetime.now(UTC)),
        )
        return MySubscription(
            updated or subscription, plan.display_name if plan else None
        )


class GetUserPlanLimitsUseCase:
    def __init__(
        self,
        plans: PlanRepositoryInterface,
        subscriptions: SubscriptionRepositoryInterface,
    ):
        self.plans = plans
        self.subscriptions = subscriptions

    def execute(self, user_id: int) -> PlanLimits:
        """The limits of the user's plan, or the free defaults if they have
        no subscription or its plan no longer exists."""
        subscription = self.subscriptions.get_by_user_id(user_id)
        plan = self.plans.get_by_id(subscription.plan_id) if subscription else None
        return limits_for_plan(plan)
