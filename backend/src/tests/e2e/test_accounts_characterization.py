"""
Characterization tests for accounts, before users and login move into an
``accounts`` module (Nov 16, 2026).

They pin today's behavior, bugs included: public sign-up had no backend test,
and three branches of "who is logged in" were uncovered. One test pins that an
invalid e-mail is refused on update, because the e-mail check moves from the
entity to the request schemas.
"""

from datetime import UTC, datetime, timedelta

from jose import jwt

from src.app.infrastructure.database.models.user_model import User as UserModel
from src.config import settings


def sign_up(client, **attributes):
    body = {
        "username": "newcomer",
        "email": "newcomer@example.com",
        "password": "Newcomer@1234",
    }
    body.update(attributes)
    return client.post(
        "/auth/register", json={"data": {"type": "users", "attributes": body}}
    )


def token_for(claims):
    claims = {**claims, "exp": datetime.now(UTC) + timedelta(minutes=5)}
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})


class TestSignUp:
    def test_a_visitor_signs_up_as_a_regular_user(self, client):
        response = sign_up(client)

        assert response.status_code == 201
        attributes = response.json()["data"]["attributes"]
        assert attributes["username"] == "newcomer"
        assert attributes["email"] == "newcomer@example.com"
        assert attributes["is_staff"] is False
        assert attributes["is_superuser"] is False
        assert "password" not in attributes
        assert "hashed_password" not in attributes
        login = client.post(
            "/auth/login",
            data={"username": "newcomer", "password": "Newcomer@1234"},
        )
        assert login.status_code == 200

    def test_sign_up_ignores_a_request_for_staff_rights(self, client, test_db):
        response = sign_up(client, is_staff=True, is_superuser=True)

        assert response.status_code == 201
        stored = test_db.query(UserModel).filter_by(username="newcomer").one()
        assert stored.is_staff is False
        assert stored.is_superuser is False

    def test_sign_up_refuses_a_taken_username(self, client, sample_user):
        response = sign_up(client, username=sample_user.username)

        assert response.status_code == 409
        assert response.json()["errors"][0]["code"] == "USERNAME_TAKEN"

    def test_sign_up_refuses_a_taken_email(self, client, sample_user):
        response = sign_up(client, email=sample_user.email)

        assert response.status_code == 409
        assert response.json()["errors"][0]["code"] == "EMAIL_TAKEN"

    def test_sign_up_refuses_an_invalid_email(self, client):
        response = sign_up(client, email="not-an-email")

        assert response.status_code == 422


class TestLoggedInUser:
    def test_a_token_without_a_username_is_refused(self, client, sample_user):
        response = me(client, token_for({}))

        assert response.status_code == 401

    def test_a_token_of_a_user_that_no_longer_exists_is_not_found(
        self, client, sample_user, test_db
    ):
        token = token_for({"sub": sample_user.username})
        test_db.delete(sample_user)
        test_db.commit()

        response = me(client, token)

        assert response.status_code == 404  # today's behavior; 401 would fit better

    def test_a_deactivated_user_is_refused(self, client, sample_user, test_db):
        token = token_for({"sub": sample_user.username})
        sample_user.is_active = False
        test_db.commit()

        response = me(client, token)

        assert response.status_code == 400


class TestUserUpdate:
    def test_an_invalid_email_is_refused_on_update(
        self, client, sample_user, superuser_auth_headers
    ):
        response = client.put(
            f"/users/{sample_user.id}",
            json={"data": {"type": "users", "attributes": {"email": "not-an-email"}}},
            headers=superuser_auth_headers,
        )

        assert response.status_code == 422


def expires_in_minutes(token):
    claims = jwt.get_unverified_claims(token)
    return (claims["exp"] - datetime.now(UTC).timestamp()) / 60


class TestTokenExpiry:
    def test_a_login_token_lasts_the_configured_minutes(self, client, sample_user):
        response = client.post(
            "/auth/login", data={"username": "testuser", "password": "Test@1234"}
        )

        token = response.json()["data"]["attributes"]["access_token"]
        minutes = expires_in_minutes(token)
        assert minutes > settings.ACCESS_TOKEN_EXPIRE_MINUTES - 1
        assert minutes <= settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def test_a_refreshed_token_lasts_the_configured_minutes(self, client, user_token):
        response = client.post(
            "/auth/refresh-token", headers={"Authorization": f"Bearer {user_token}"}
        )

        token = response.json()["data"]["attributes"]["access_token"]
        minutes = expires_in_minutes(token)
        assert minutes > settings.ACCESS_TOKEN_EXPIRE_MINUTES - 1
        assert minutes <= settings.ACCESS_TOKEN_EXPIRE_MINUTES
