"""Characterization tests before the billing module (plans and subscriptions).

They pin today's behavior over HTTP, so the refactor that moves plans,
subscriptions and plan limits into ``src/app/billing`` can prove it
changed nothing.
"""

from src.app.infrastructure.database.models.plan_model import Plan as PlanModel
from src.app.infrastructure.database.models.subscription_model import (
    Subscription as SubscriptionModel,
)
from src.tests.e2e.test_subscription_controller import _seed_plans


def subscribe(test_db, user_id, plan_id):
    test_db.add(SubscriptionModel(user_id=user_id, plan_id=plan_id, status="active"))
    test_db.commit()


def my_plan_name(client, headers):
    response = client.get("/subscriptions/me", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]["attributes"]["plan_name"]


class TestSubscribe:
    def test_a_plan_no_longer_offered_cannot_be_subscribed(
        self, client, test_db, auth_headers
    ):
        _seed_plans(test_db)
        test_db.add(
            PlanModel(id=4, name="legacy", display_name="Legacy", is_active=False)
        )
        test_db.commit()

        response = client.post("/subscriptions/subscribe/4", headers=auth_headers)

        assert response.status_code == 400
        assert response.json()["errors"][0]["code"] == "PLAN_INACTIVE"
        assert my_plan_name(client, auth_headers) == "Free"

    def test_subscribing_makes_the_new_plan_the_users_plan(
        self, client, test_db, sample_user, auth_headers
    ):
        _seed_plans(test_db)
        subscribe(test_db, sample_user.id, 2)

        response = client.post("/subscriptions/subscribe/3", headers=auth_headers)

        assert response.status_code == 200
        assert my_plan_name(client, auth_headers) == "Business"


class TestCancel:
    def test_a_user_subscribed_to_the_free_plan_cannot_cancel(
        self, client, test_db, sample_user, auth_headers
    ):
        _seed_plans(test_db)
        subscribe(test_db, sample_user.id, 1)

        response = client.post("/subscriptions/cancel", headers=auth_headers)

        assert response.status_code == 400
        assert response.json()["errors"][0]["code"] == "ALREADY_FREE"

    def test_after_canceling_the_user_is_back_on_the_free_plan(
        self, client, test_db, sample_user, auth_headers
    ):
        _seed_plans(test_db)
        subscribe(test_db, sample_user.id, 2)

        client.post("/subscriptions/cancel", headers=auth_headers)

        assert my_plan_name(client, auth_headers) == "Free"


class TestMySubscriptionWithoutPlans:
    def test_with_no_plans_in_the_database_the_user_sees_a_free_plan(
        self, client, auth_headers
    ):
        response = client.get("/subscriptions/me", headers=auth_headers)

        attributes = response.json()["data"]["attributes"]
        assert attributes["plan_name"] == "Free"
        assert attributes["plan_id"] == 0
