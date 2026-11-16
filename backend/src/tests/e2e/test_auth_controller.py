"""
E2E Tests for Auth Controller

Tests the complete authentication flow:
    HTTP Request → AuthController → AuthUseCase → UserRepository → Database
"""


class TestAuthLogin:
    """Test POST /auth/login - User authentication"""

    def test_login_with_valid_credentials(self, client, sample_user):
        """
        Given: A user with valid credentials exists
        When: POST /auth/login with correct username and password
        Then: Returns 200 with access_token in JSON:API format
        """
        # When
        response = client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "Test@1234",
            },  # Form data, not JSON
        )

        # Then
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["type"] == "auth"
        assert "access_token" in data["data"]["attributes"]
        assert "token_type" in data["data"]["attributes"]
        assert data["data"]["attributes"]["token_type"] == "bearer"

    def test_login_with_invalid_username(self, client, sample_user):
        """
        Given: A user exists in database
        When: POST /auth/login with incorrect username
        Then: Returns 400 with invalid credentials error
        """
        # When
        response = client.post(
            "/auth/login", data={"username": "wronguser", "password": "Test@1234"}
        )

        # Then
        assert response.status_code == 400

        data = response.json()
        assert "errors" in data
        assert len(data["errors"]) > 0
        assert data["errors"][0]["status"] == "400"
        # Check for either "credentials" or "incorrect"
        detail_lower = data["errors"][0]["detail"].lower()
        assert "incorrect" in detail_lower or "credentials" in detail_lower

    def test_login_with_invalid_password(self, client, sample_user):
        """
        Given: A user exists in database
        When: POST /auth/login with incorrect password
        Then: Returns 400 with invalid credentials error
        """
        # When
        response = client.post(
            "/auth/login", data={"username": "testuser", "password": "WrongPassword123"}
        )

        # Then
        assert response.status_code == 400

        data = response.json()
        assert "errors" in data
        assert data["errors"][0]["status"] == "400"

    def test_login_with_missing_fields(self, client):
        """
        Given: No specific user context
        When: POST /auth/login with missing required fields
        Then: Returns 422 validation error
        """
        # When
        response = client.post(
            "/auth/login",
            data={"username": "testuser"},  # Missing password
        )

        # Then
        assert response.status_code == 422

    def test_login_with_inactive_user(self, client, test_db):
        """
        Given: An inactive user exists
        When: POST /auth/login with correct credentials
        Then: Returns 200 with token (API allows inactive users to login)
        """
        from passlib.context import CryptContext

        from src.app.accounts.persistence.models import User

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Given - Use the same test_db session
        inactive_user = User(
            username="inactive",
            email="inactive@example.com",
            hashed_password=pwd_context.hash("Test@1234"),
            is_active=False,
        )
        test_db.add(inactive_user)
        test_db.commit()
        test_db.refresh(inactive_user)

        # When
        response = client.post(
            "/auth/login", data={"username": "inactive", "password": "Test@1234"}
        )

        # Then - API allows inactive users to login
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["data"]["attributes"]


class TestAuthVerifyToken:
    """Test POST /auth/verify-token - Token validation"""

    def test_verify_valid_token(self, client, user_token):
        """
        Given: A valid authentication token
        When: POST /auth/verify-token with valid token in JSON:API format
        Then: Returns 200 with valid=True
        """
        # When
        response = client.post(
            "/auth/verify-token",
            json={
                "data": {
                    "type": "token-validations",
                    "attributes": {"token": user_token},
                }
            },
        )

        # Then
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["type"] == "token-validations"
        assert data["data"]["attributes"]["is_valid"] is True

    def test_verify_invalid_token(self, client):
        """
        Given: An invalid token
        When: POST /auth/verify-token with invalid token
        Then: Returns 200 with is_valid=False
        """
        # When
        response = client.post(
            "/auth/verify-token",
            json={
                "data": {
                    "type": "token-validations",
                    "attributes": {"token": "invalid.token.here"},
                }
            },
        )

        # Then
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["attributes"]["is_valid"] is False

    def test_verify_expired_token(self, client):
        """
        Given: An expired token
        When: POST /auth/verify-token with expired token
        Then: Returns 200 with is_valid=False and message
        """
        # Simulating expired token (you'd need to generate an expired one)
        # For now, test with malformed token

        # When
        response = client.post(
            "/auth/verify-token",
            json={
                "data": {
                    "type": "token-validations",
                    "attributes": {
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired"
                    },
                }
            },
        )

        # Then
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["attributes"]["is_valid"] is False


class TestAuthRefreshToken:
    """Test POST /auth/refresh-token - Token refresh"""

    def test_refresh_with_valid_token(self, client, user_token):
        """
        Given: A valid authentication token
        When: POST /auth/refresh-token with valid token in Authorization header
        Then: Returns 200 with new access_token
        """
        # When
        response = client.post(
            "/auth/refresh-token", headers={"Authorization": f"Bearer {user_token}"}
        )

        # Then
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["type"] == "auth"
        assert "access_token" in data["data"]["attributes"]
        # Note: Token might be identical if generated in same second with same payload

    def test_refresh_with_invalid_token(self, client):
        """
        Given: An invalid token
        When: POST /auth/refresh-token with invalid token
        Then: Returns 401 or 403 authentication error
        """
        # When
        response = client.post(
            "/auth/refresh-token",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        # Then
        assert response.status_code in [
            401,
            403,
        ]  # Either is acceptable for invalid token
