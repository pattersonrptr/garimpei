"""Billing's subscription use cases, with in-memory fakes for the ports."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from src.app.billing.entities import Plan, Subscription
from src.app.billing.ports import (
    PlanRepositoryInterface,
    SubscriptionRepositoryInterface,
)
from src.app.billing.use_cases import (
    AlreadyFreeError,
    CancelSubscriptionUseCase,
    GetMySubscriptionUseCase,
    NoSubscriptionError,
    PlanInactiveError,
    PlanNotFoundError,
    SubscribeUseCase,
)

USER = 7
MEMBER_SINCE = datetime(2026, 1, 15, tzinfo=UTC)
FREE = Plan(id=1, name="free", display_name="Free")
PRO = Plan(id=2, name="pro", display_name="Pro", price_cents=2900)
LEGACY = Plan(id=4, name="legacy", display_name="Legacy", is_active=False)


class FakePlans(PlanRepositoryInterface):
    def __init__(self, *plans: Plan):
        self.plans = {p.id: p for p in plans}

    def create(self, plan: Plan) -> Plan:
        created = replace(plan, id=max(self.plans, default=0) + 1)
        self.plans[created.id] = created
        return created

    def get_by_id(self, plan_id: int) -> Plan | None:
        return self.plans.get(plan_id)

    def get_by_name(self, name: str) -> Plan | None:
        return next((p for p in self.plans.values() if p.name == name), None)

    def get_all(self) -> list[Plan]:
        return [p for p in self.plans.values() if p.is_active]


class FakeSubscriptions(SubscriptionRepositoryInterface):
    def __init__(self, *subscriptions: Subscription):
        self.rows = {s.id: s for s in subscriptions}

    def create(self, subscription: Subscription) -> Subscription:
        created = replace(subscription, id=max(self.rows, default=0) + 1)
        self.rows[created.id] = created
        return created

    def get_by_user_id(self, user_id: int) -> Subscription | None:
        return next(
            (
                s
                for s in self.rows.values()
                if s.user_id == user_id and s.status == "active"
            ),
            None,
        )

    def update(
        self, subscription_id: int, subscription: Subscription
    ) -> Subscription | None:
        if subscription_id not in self.rows:
            return None
        self.rows[subscription_id] = replace(subscription, id=subscription_id)
        return self.rows[subscription_id]


def subscribed_to(plan: Plan) -> FakeSubscriptions:
    return FakeSubscriptions(Subscription(id=10, user_id=USER, plan_id=plan.id))


class TestMySubscription:
    def test_a_subscriber_sees_their_subscription_and_plan_name(self):
        mine = GetMySubscriptionUseCase(FakePlans(FREE, PRO), subscribed_to(PRO))

        result = mine.execute(USER, member_since=MEMBER_SINCE)

        assert (result.subscription.id, result.subscription.plan_id) == (10, 2)
        assert result.plan_name == "Pro"

    def test_without_a_subscription_the_user_is_on_free_since_joining(self):
        mine = GetMySubscriptionUseCase(FakePlans(FREE, PRO), FakeSubscriptions())

        result = mine.execute(USER, member_since=MEMBER_SINCE)

        assert result.subscription.id == 0
        assert result.subscription.user_id == USER
        assert result.subscription.plan_id == FREE.id
        assert result.subscription.status == "active"
        assert result.subscription.current_period_start == MEMBER_SINCE
        assert result.subscription.current_period_end is None
        assert result.plan_name == "Free"

    def test_with_no_plans_at_all_the_free_plan_has_id_0(self):
        mine = GetMySubscriptionUseCase(FakePlans(), FakeSubscriptions())

        result = mine.execute(USER, member_since=MEMBER_SINCE)

        assert (result.subscription.plan_id, result.plan_name) == (0, "Free")


class TestSubscribe:
    def test_an_unknown_plan_cannot_be_subscribed(self):
        subscribe = SubscribeUseCase(FakePlans(FREE), FakeSubscriptions())

        with pytest.raises(PlanNotFoundError):
            subscribe.execute(USER, plan_id=99)

    def test_a_plan_no_longer_offered_cannot_be_subscribed(self):
        subscriptions = subscribed_to(PRO)
        subscribe = SubscribeUseCase(FakePlans(FREE, PRO, LEGACY), subscriptions)

        with pytest.raises(PlanInactiveError):
            subscribe.execute(USER, plan_id=LEGACY.id)

        assert subscriptions.get_by_user_id(USER).plan_id == PRO.id

    def test_subscribing_cancels_the_current_plan_and_starts_the_new_one(self):
        subscriptions = subscribed_to(FREE)
        subscribe = SubscribeUseCase(FakePlans(FREE, PRO), subscriptions)

        result = subscribe.execute(USER, plan_id=PRO.id)

        old = subscriptions.rows[10]
        assert old.status == "canceled"
        assert old.canceled_at is not None
        assert result.subscription.plan_id == PRO.id
        assert result.subscription.status == "active"
        assert result.plan_name == "Pro"
        assert subscriptions.get_by_user_id(USER) == result.subscription


class TestCancel:
    def test_a_user_without_a_subscription_has_nothing_to_cancel(self):
        cancel = CancelSubscriptionUseCase(FakePlans(FREE), FakeSubscriptions())

        with pytest.raises(NoSubscriptionError):
            cancel.execute(USER)

    def test_a_user_on_the_free_plan_cannot_cancel(self):
        cancel = CancelSubscriptionUseCase(FakePlans(FREE), subscribed_to(FREE))

        with pytest.raises(AlreadyFreeError):
            cancel.execute(USER)

    def test_canceling_ends_the_paid_subscription(self):
        subscriptions = subscribed_to(PRO)
        cancel = CancelSubscriptionUseCase(FakePlans(FREE, PRO), subscriptions)

        result = cancel.execute(USER)

        assert result.subscription.status == "canceled"
        assert result.subscription.canceled_at is not None
        assert result.plan_name == "Pro"
        assert subscriptions.get_by_user_id(USER) is None
