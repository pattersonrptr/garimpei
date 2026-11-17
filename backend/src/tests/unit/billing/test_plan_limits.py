"""GetUserPlanLimitsUseCase: what a user's plan allows."""

from src.app.billing.entities import Plan, Subscription
from src.app.billing.limits import FREE_PLAN_DEFAULTS
from src.app.billing.use_cases import GetUserPlanLimitsUseCase
from src.tests.unit.billing.test_subscriptions import (
    FREE,
    USER,
    FakePlans,
    FakeSubscriptions,
)

BUSINESS = Plan(
    id=3,
    name="business",
    display_name="Business",
    max_active_alerts=None,
    min_frequency_minutes=15,
    price_history_days=None,
    max_sources=None,
)
PRO = Plan(
    id=2,
    name="pro",
    display_name="Pro",
    max_active_alerts=20,
    min_frequency_minutes=30,
    price_history_days=90,
    max_sources=5,
)


def subscribed_to(plan_id: int) -> FakeSubscriptions:
    return FakeSubscriptions(Subscription(id=10, user_id=USER, plan_id=plan_id))


def test_a_subscriber_gets_every_limit_of_their_plan():
    limits = GetUserPlanLimitsUseCase(
        FakePlans(FREE, PRO), subscribed_to(PRO.id)
    ).execute(USER)

    assert limits.plan_name == "pro"
    assert limits.max_active_alerts == 20
    assert limits.min_frequency_minutes == 30
    assert limits.price_history_days == 90
    assert limits.max_sources == 5


def test_unlimited_stays_unlimited():
    limits = GetUserPlanLimitsUseCase(
        FakePlans(BUSINESS), subscribed_to(BUSINESS.id)
    ).execute(USER)

    assert limits.max_active_alerts is None
    assert limits.price_history_days is None
    assert limits.max_sources is None


def test_without_a_subscription_the_user_gets_the_free_defaults():
    limits = GetUserPlanLimitsUseCase(FakePlans(FREE), FakeSubscriptions()).execute(
        USER
    )

    assert limits.plan_name == "free"
    assert limits.max_active_alerts == FREE_PLAN_DEFAULTS["max_active_alerts"]
    assert limits.min_frequency_minutes == FREE_PLAN_DEFAULTS["min_frequency_minutes"]
    assert limits.price_history_days == FREE_PLAN_DEFAULTS["price_history_days"]
    assert limits.max_sources == FREE_PLAN_DEFAULTS["max_sources"]


def test_a_subscription_to_a_removed_plan_gets_the_free_defaults():
    limits = GetUserPlanLimitsUseCase(FakePlans(FREE), subscribed_to(99)).execute(USER)

    assert limits.plan_name == "free"
    assert limits.max_active_alerts == FREE_PLAN_DEFAULTS["max_active_alerts"]
