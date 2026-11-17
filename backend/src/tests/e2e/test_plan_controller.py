"""
E2E tests for Plan controller.

Tests:
- GET /plans/ — list all active plans (public)
- GET /plans/{id} — get single plan
- POST /plans/ — create plan (superuser only)
"""

from src.app.billing.persistence.models import Plan as PlanModel

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
# GET /plans/ Tests
# ============================================================================


class TestListPlans:
    """Tests for GET /plans/."""

    def test_list_plans_should_return_all_active_plans(self, client, test_db):
        """
        Given: Three active plans in the database
        When: GET /plans/ is called (no auth required)
        Then: Should return all plans sorted by price
        """
        _seed_plans(test_db)

        response = client.get("/plans/")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 3
        assert data[0]["attributes"]["name"] == "free"
        assert data[1]["attributes"]["name"] == "pro"
        assert data[2]["attributes"]["name"] == "business"

    def test_list_plans_should_return_empty_when_no_plans(self, client):
        """
        Given: No plans in the database
        When: GET /plans/ is called
        Then: Should return empty collection
        """
        response = client.get("/plans/")

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 0

    def test_list_plans_should_return_correct_attributes(self, client, test_db):
        """
        Given: Plans with full attributes
        When: GET /plans/ is called
        Then: Should return all plan attributes
        """
        _seed_plans(test_db)

        response = client.get("/plans/")

        data = response.json()["data"]
        free_plan = data[0]["attributes"]
        assert free_plan["name"] == "free"
        assert free_plan["display_name"] == "Free"
        assert free_plan["price_cents"] == 0
        assert free_plan["max_active_alerts"] == 3
        assert free_plan["min_frequency_minutes"] == 360
        assert free_plan["price_history_days"] == 7
        assert free_plan["max_sources"] == 2
        assert free_plan["has_push_notifications"] is False


# ============================================================================
# GET /plans/{id} Tests
# ============================================================================


class TestGetPlan:
    """Tests for GET /plans/{id}."""

    def test_get_plan_by_id_should_return_plan(self, client, test_db):
        """
        Given: A plan exists in the database
        When: GET /plans/{id} is called
        Then: Should return the plan
        """
        _seed_plans(test_db)

        response = client.get("/plans/2")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["attributes"]["name"] == "pro"
        assert data["attributes"]["price_cents"] == 2900

    def test_get_plan_not_found_should_return_404(self, client, test_db):
        """
        Given: No plan with the given ID
        When: GET /plans/{id} is called
        Then: Should return 404
        """
        _seed_plans(test_db)

        response = client.get("/plans/999")

        assert response.status_code == 404


# ============================================================================
# POST /plans/ Tests
# ============================================================================


class TestCreatePlan:
    """Tests for POST /plans/."""

    def test_create_plan_as_superuser_should_succeed(
        self, client, superuser_auth_headers
    ):
        """
        Given: A superuser with valid plan data
        When: POST /plans/ is called
        Then: Should create the plan and return 201
        """
        payload = {
            "data": {
                "type": "plans",
                "attributes": {
                    "name": "enterprise",
                    "display_name": "Enterprise",
                    "price_cents": 19900,
                    "max_active_alerts": None,
                    "min_frequency_minutes": 5,
                    "price_history_days": None,
                    "max_sources": None,
                    "has_push_notifications": True,
                    "has_whatsapp_notifications": True,
                    "has_api_access": True,
                },
            }
        }

        response = client.post("/plans/", json=payload, headers=superuser_auth_headers)

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["attributes"]["name"] == "enterprise"
        assert data["attributes"]["price_cents"] == 19900

    def test_create_plan_as_regular_user_should_fail(self, client, auth_headers):
        """
        Given: A regular user
        When: POST /plans/ is called
        Then: Should return 403
        """
        payload = {
            "data": {
                "type": "plans",
                "attributes": {
                    "name": "hacker",
                    "display_name": "Hacker",
                    "price_cents": 0,
                    "min_frequency_minutes": 1,
                },
            }
        }

        response = client.post("/plans/", json=payload, headers=auth_headers)

        assert response.status_code == 403

    def test_create_plan_without_auth_should_fail(self, client):
        """
        Given: No authentication
        When: POST /plans/ is called
        Then: Should return 401 or 403
        """
        payload = {
            "data": {
                "type": "plans",
                "attributes": {
                    "name": "test",
                    "display_name": "Test",
                    "price_cents": 0,
                    "min_frequency_minutes": 60,
                },
            }
        }

        response = client.post("/plans/", json=payload)

        assert response.status_code in (401, 403)
