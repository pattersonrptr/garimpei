"""Alerts apply the user's plan limits (CheckAlertLimitsUseCase, with fakes)."""

from dataclasses import replace
from unittest.mock import MagicMock

from src.app.alerts.entities import AlertLimits, PriceAlert
from src.app.alerts.persistence.plan_limits import BillingAlertLimits
from src.app.alerts.ports import AlertLimitsReader
from src.app.alerts.use_cases import CheckAlertLimitsUseCase
from src.app.billing.entities import Plan, Subscription
from src.app.billing.use_cases import GetUserPlanLimitsUseCase
from src.tests.unit.billing.test_subscriptions import FakePlans, FakeSubscriptions

USER = 7
FREE = AlertLimits(
    plan_name="free", max_active_alerts=3, min_frequency_minutes=360, max_sources=2
)
UNLIMITED = AlertLimits(
    plan_name="business",
    max_active_alerts=None,
    min_frequency_minutes=15,
    max_sources=None,
)


class FixedLimits(AlertLimitsReader):
    def __init__(self, limits: AlertLimits):
        self.limits = limits

    def for_user(self, user_id: int) -> AlertLimits:
        return self.limits


def check(limits: AlertLimits, active_alerts: int = 0) -> CheckAlertLimitsUseCase:
    alerts = MagicMock()
    alerts.count_active_by_user_id.return_value = active_alerts
    return CheckAlertLimitsUseCase(FixedLimits(limits), alerts)


def alert(**changes) -> PriceAlert:
    base = PriceAlert(
        id=1,
        search_term="duna",
        max_price=50,
        user_id=USER,
        is_active=True,
        frequency_minutes=720,
        source_website_ids=[1, 2],
    )
    return replace(base, **changes)


class TestNewAlert:
    def test_an_alert_within_every_limit_is_allowed(self):
        assert (
            check(FREE, active_alerts=2).for_new_alert(
                USER, frequency_minutes=360, source_count=2
            )
            is None
        )

    def test_the_plan_caps_how_many_alerts_are_active(self):
        violation = check(FREE, active_alerts=3).for_new_alert(
            USER, frequency_minutes=720, source_count=1
        )

        assert violation is not None
        assert violation.meta == {
            "limit": "max_active_alerts",
            "value": 3,
            "plan": "free",
        }
        assert violation.pointer == "/data/attributes/is_active"
        assert "up to 3 active alerts" in violation.detail

    def test_unlimited_alerts_ignore_the_count(self):
        assert (
            check(UNLIMITED, active_alerts=500).for_new_alert(
                USER, frequency_minutes=15, source_count=9
            )
            is None
        )

    def test_checking_more_often_than_the_plan_allows_is_refused(self):
        violation = check(FREE).for_new_alert(
            USER, frequency_minutes=359, source_count=1
        )

        assert violation is not None
        assert violation.meta == {
            "limit": "min_frequency_minutes",
            "value": 360,
            "plan": "free",
        }
        assert violation.pointer == "/data/attributes/frequency_minutes"

    def test_more_stores_than_the_plan_allows_is_refused(self):
        violation = check(FREE).for_new_alert(
            USER, frequency_minutes=360, source_count=3
        )

        assert violation is not None
        assert violation.meta == {"limit": "max_sources", "value": 2, "plan": "free"}
        assert violation.pointer == "/data/attributes/source_website_ids"

    def test_the_active_alert_limit_is_reported_first(self):
        violation = check(FREE, active_alerts=3).for_new_alert(
            USER, frequency_minutes=30, source_count=9
        )

        assert violation is not None
        assert violation.meta["limit"] == "max_active_alerts"


class TestChangedAlert:
    def test_reactivating_a_paused_alert_counts_against_the_active_limit(self):
        violation = check(FREE, active_alerts=3).for_changes(
            alert(is_active=False), alert(is_active=True)
        )

        assert violation is not None
        assert violation.meta["limit"] == "max_active_alerts"

    def test_editing_an_active_alert_does_not_count_it_again(self):
        assert (
            check(FREE, active_alerts=3).for_changes(alert(), alert(max_price=40))
            is None
        )

    def test_a_frequency_left_unchanged_is_not_checked_again(self):
        old_plan_frequency = alert(frequency_minutes=60)

        assert (
            check(FREE).for_changes(
                old_plan_frequency, replace(old_plan_frequency, max_price=40)
            )
            is None
        )

    def test_a_changed_frequency_must_fit_the_plan(self):
        violation = check(FREE).for_changes(alert(), alert(frequency_minutes=60))

        assert violation is not None
        assert violation.meta["limit"] == "min_frequency_minutes"

    def test_changed_stores_must_fit_the_plan(self):
        violation = check(FREE).for_changes(
            alert(), alert(source_website_ids=[1, 2, 3])
        )

        assert violation is not None
        assert violation.meta["limit"] == "max_sources"

    def test_the_same_stores_in_another_order_are_not_a_change(self):
        too_many = alert(source_website_ids=[1, 2, 3])

        assert (
            check(FREE).for_changes(
                too_many, replace(too_many, source_website_ids=[3, 2, 1])
            )
            is None
        )


class TestLimitsFromBilling:
    def test_alerts_read_the_limits_of_the_users_plan_in_billing(self):
        pro = Plan(
            id=2,
            name="pro",
            display_name="Pro",
            max_active_alerts=20,
            min_frequency_minutes=30,
            max_sources=5,
        )
        billing = GetUserPlanLimitsUseCase(
            FakePlans(pro),
            FakeSubscriptions(Subscription(id=10, user_id=USER, plan_id=2)),
        )

        limits = BillingAlertLimits(billing).for_user(USER)

        assert limits == AlertLimits(
            plan_name="pro",
            max_active_alerts=20,
            min_frequency_minutes=30,
            max_sources=5,
        )
