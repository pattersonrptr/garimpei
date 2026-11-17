"""
E2E tests for Subscription controller.

Tests:
- GET /subscriptions/me — get current subscription
- POST /subscriptions/subscribe/{plan_id} — subscribe to a plan
- POST /subscriptions/cancel — cancel current subscription
- GET /subscriptions/me/limits — get current plan limits
"""

from src.app.billing.persistence.models import Plan as PlanModel
from src.app.billing.persistence.models import Subscription as SubscriptionModel

# ============================================================================
# Fixtures
# ============================================================================


def _seed_plans(test_db):
    """Seed the three default plans."""
    plans = [
        PlanModel(
            id=1,
            name="free",
            display_name="Free",
            price_cents=0,
            max_active_alerts=3,
            min_frequency_minutes=360,
            price_history_days=7,
            max_sources=2,
            has_push_notifications=False,
            has_whatsapp_notifications=False,
            has_api_access=False,
            is_active=True,
        ),
        PlanModel(
            id=2,
            name="pro",
            display_name="Pro",
            price_cents=2900,
            max_active_alerts=None,
            min_frequency_minutes=30,
            price_history_days=90,
            max_sources=None,
            has_push_notifications=True,
            has_whatsapp_notifications=False,
            has_api_access=False,
            is_active=True,
        ),
        PlanModel(
            id=3,
            name="business",
            display_name="Business",
            price_cents=7900,
            max_active_alerts=None,
            min_frequency_minutes=15,
            price_history_days=None,
            max_sources=None,
            has_push_notifications=True,
            has_whatsapp_notifications=True,
            has_api_access=True,
            is_active=True,
        ),
    ]
    for plan in plans:
        test_db.add(plan)
    test_db.commit()
    return plans


# ============================================================================
# GET /subscriptions/me Tests
# ============================================================================


class TestGetMySubscription:
    """Tests for GET /subscriptions/me."""

    def test_no_subscription_should_return_free_plan(
        self, client, test_db, auth_headers
    ):
        """
        Given: User with no subscription
        When: GET /subscriptions/me is called
        Then: Should return synthesized free plan subscription
        """
        _seed_plans(test_db)

        response = client.get("/subscriptions/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["attributes"]["plan_name"] == "Free"
        assert data["attributes"]["status"] == "active"

    def test_with_subscription_should_return_current_plan(
        self, client, test_db, sample_user, auth_headers
    ):
        """
        Given: User with an active pro subscription
        When: GET /subscriptions/me is called
        Then: Should return the pro subscription
        """
        _seed_plans(test_db)
        sub = SubscriptionModel(
            user_id=sample_user.id,
            plan_id=2,
            status="active",
        )
        test_db.add(sub)
        test_db.commit()

        response = client.get("/subscriptions/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["attributes"]["plan_name"] == "Pro"
        assert data["attributes"]["status"] == "active"

    def test_without_auth_should_return_401(self, client):
        """
        Given: No authentication
        When: GET /subscriptions/me is called
        Then: Should return 401 or 403
        """
        response = client.get("/subscriptions/me")
        assert response.status_code in (401, 403)


# ============================================================================
# POST /subscriptions/subscribe/{plan_id} Tests
# ============================================================================


class TestSubscribeToPlan:
    """Tests for POST /subscriptions/subscribe/{plan_id}."""

    def test_subscribe_to_pro_should_create_subscription(
        self, client, test_db, auth_headers
    ):
        """
        Given: User without subscription and pro plan available
        When: POST /subscriptions/subscribe/2 is called
        Then: Should create active subscription
        """
        _seed_plans(test_db)

        response = client.post("/subscriptions/subscribe/2", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["attributes"]["plan_name"] == "Pro"
        assert data["attributes"]["status"] == "active"

    def test_subscribe_to_invalid_plan_should_return_404(
        self, client, test_db, auth_headers
    ):
        """
        Given: Plan ID that doesn't exist
        When: POST /subscriptions/subscribe/999 is called
        Then: Should return 404
        """
        _seed_plans(test_db)

        response = client.post("/subscriptions/subscribe/999", headers=auth_headers)

        assert response.status_code == 404

    def test_subscribe_should_cancel_existing_subscription(
        self, client, test_db, sample_user, auth_headers
    ):
        """
        Given: User with active pro subscription
        When: POST /subscriptions/subscribe/3 (business) is called
        Then: Should cancel pro and create business subscription
        """
        _seed_plans(test_db)
        # Create existing pro subscription
        sub = SubscriptionModel(
            user_id=sample_user.id,
            plan_id=2,
            status="active",
        )
        test_db.add(sub)
        test_db.commit()

        response = client.post("/subscriptions/subscribe/3", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["attributes"]["plan_name"] == "Business"
        assert data["attributes"]["status"] == "active"

    def test_subscribe_without_auth_should_return_401(self, client, test_db):
        """
        Given: No authentication
        When: POST /subscriptions/subscribe/2 is called
        Then: Should return 401 or 403
        """
        _seed_plans(test_db)

        response = client.post("/subscriptions/subscribe/2")
        assert response.status_code in (401, 403)


# ============================================================================
# POST /subscriptions/cancel Tests
# ============================================================================


class TestCancelSubscription:
    """Tests for POST /subscriptions/cancel."""

    def test_cancel_active_subscription_should_return_canceled(
        self, client, test_db, sample_user, auth_headers
    ):
        """
        Given: User with active subscription
        When: POST /subscriptions/cancel is called
        Then: Should return subscription with canceled status
        """
        _seed_plans(test_db)
        sub = SubscriptionModel(
            user_id=sample_user.id,
            plan_id=2,
            status="active",
        )
        test_db.add(sub)
        test_db.commit()

        response = client.post("/subscriptions/cancel", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["attributes"]["status"] == "canceled"

    def test_cancel_without_subscription_should_return_400(
        self, client, test_db, auth_headers
    ):
        """
        Given: User with no active subscription
        When: POST /subscriptions/cancel is called
        Then: Should return 400
        """
        _seed_plans(test_db)

        response = client.post("/subscriptions/cancel", headers=auth_headers)

        assert response.status_code == 400


# ============================================================================
# GET /subscriptions/me/limits Tests
# ============================================================================


class TestGetMyLimits:
    """Tests for GET /subscriptions/me/limits."""

    def test_free_user_should_get_free_limits(self, client, test_db, auth_headers):
        """
        Given: User without subscription
        When: GET /subscriptions/me/limits is called
        Then: Should return free plan limits
        """
        _seed_plans(test_db)

        response = client.get("/subscriptions/me/limits", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        attrs = data["attributes"]
        assert attrs["plan_name"] == "free"
        assert attrs["max_active_alerts"] == 3
        assert attrs["min_frequency_minutes"] == 360
        assert attrs["price_history_days"] == 7
        assert attrs["max_sources"] == 2

    def test_pro_user_should_get_pro_limits(
        self, client, test_db, sample_user, auth_headers
    ):
        """
        Given: User with pro subscription
        When: GET /subscriptions/me/limits is called
        Then: Should return pro plan limits
        """
        _seed_plans(test_db)
        sub = SubscriptionModel(
            user_id=sample_user.id,
            plan_id=2,
            status="active",
        )
        test_db.add(sub)
        test_db.commit()

        response = client.get("/subscriptions/me/limits", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        attrs = data["attributes"]
        assert attrs["plan_name"] == "pro"
        assert attrs["max_active_alerts"] is None
        assert attrs["min_frequency_minutes"] == 30
        assert attrs["max_sources"] is None

    def test_limits_without_auth_should_return_401_or_403(self, client):
        """
        Given: No authentication
        When: GET /subscriptions/me/limits is called
        Then: Should return 401 or 403
        """
        response = client.get("/subscriptions/me/limits")
        assert response.status_code in (401, 403)
