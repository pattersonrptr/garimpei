"""
Unit tests for Auth Presenter.

Tests authentication presentation layer (JSON:API formatting).
Following Given/When/Then pattern for clarity.
"""

from fastapi.responses import JSONResponse

from src.app.accounts.http.auth_presenter import AuthPresenter

# ============================================================================
# AuthPresenter.present_token Tests
# ============================================================================


class TestAuthPresenterPresentToken:
    """Tests for AuthPresenter.present_token()."""

    def test_present_token_should_return_jsonapi_token_response(self):
        """
        Given: Valid token data
        When: AuthPresenter.present_token() is called
        Then: Should return TokenResponse with correct JSON:API structure
        """
        # Given
        access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        token_type = "bearer"
        expires_in = 1440

        # When
        response = AuthPresenter.present_token(
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
        )

        # Then
        assert response.data.type == "auth"
        assert response.data.attributes.access_token == access_token
        assert response.data.attributes.token_type == token_type
        assert response.data.attributes.expires_in == expires_in

    def test_present_token_should_use_default_values(self):
        """
        Given: Only access_token provided
        When: AuthPresenter.present_token() is called
        Then: Should use default values for token_type and expires_in
        """
        # Given
        access_token = "test_token"

        # When
        response = AuthPresenter.present_token(access_token=access_token)

        # Then
        assert response.data.attributes.token_type == "bearer"
        assert response.data.attributes.expires_in == 1440

    def test_present_token_should_include_meta_when_provided(self):
        """
        Given: Token data with meta information
        When: AuthPresenter.present_token() is called
        Then: Should include meta in response
        """
        # Given
        access_token = "test_token"
        meta = {"user_id": 1, "username": "testuser"}

        # When
        response = AuthPresenter.present_token(
            access_token=access_token,
            meta=meta,
        )

        # Then
        assert response.meta == meta
        assert response.meta["user_id"] == 1
        assert response.meta["username"] == "testuser"

    def test_present_token_should_have_no_meta_when_not_provided(self):
        """
        Given: Token data without meta
        When: AuthPresenter.present_token() is called
        Then: Should have None meta
        """
        # Given
        access_token = "test_token"

        # When
        response = AuthPresenter.present_token(access_token=access_token)

        # Then
        assert response.meta is None


# ============================================================================
# AuthPresenter.present_token_validation Tests
# ============================================================================


class TestAuthPresenterPresentTokenValidation:
    """Tests for AuthPresenter.present_token_validation()."""

    def test_present_token_validation_should_return_valid_response(self):
        """
        Given: Valid token (is_valid=True)
        When: AuthPresenter.present_token_validation() is called
        Then: Should return validation response with is_valid=True
        """
        # When
        response = AuthPresenter.present_token_validation(
            is_valid=True, message="Token is valid"
        )

        # Then
        assert response.data.type == "token-validations"
        assert response.data.attributes.is_valid is True
        assert response.data.attributes.message == "Token is valid"

    def test_present_token_validation_should_return_invalid_response(self):
        """
        Given: Invalid token (is_valid=False)
        When: AuthPresenter.present_token_validation() is called
        Then: Should return validation response with is_valid=False
        """
        # When
        response = AuthPresenter.present_token_validation(
            is_valid=False, message="Token expired"
        )

        # Then
        assert response.data.attributes.is_valid is False
        assert response.data.attributes.message == "Token expired"

    def test_present_token_validation_should_work_without_message(self):
        """
        Given: Validation result without message
        When: AuthPresenter.present_token_validation() is called
        Then: Should return response with None message
        """
        # When
        response = AuthPresenter.present_token_validation(is_valid=True)

        # Then
        assert response.data.attributes.is_valid is True
        assert response.data.attributes.message is None


# ============================================================================
# AuthPresenter.handle_authentication_error Tests
# ============================================================================


class TestAuthPresenterHandleAuthenticationError:
    """Tests for AuthPresenter.handle_authentication_error()."""

    def test_handle_authentication_error_should_return_401_jsonapi_error(self):
        """
        Given: Authentication error detail
        When: AuthPresenter.handle_authentication_error() is called
        Then: Should return 401 JSONResponse with JSON:API error structure
        """
        # Given
        detail = "Token has expired"

        # When
        response = AuthPresenter.handle_authentication_error(detail)

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        assert response.media_type == "application/vnd.api+json"

    def test_handle_authentication_error_should_include_detail_in_response(self):
        """
        Given: Specific error detail
        When: AuthPresenter.handle_authentication_error() is called
        Then: Should include detail in error response
        """
        # Given
        detail = "Invalid token signature"

        # When
        response = AuthPresenter.handle_authentication_error(detail)
        content = response.body.decode("utf-8")

        # Then
        assert "Invalid token signature" in content
        assert "AUTHENTICATION_FAILED" in content
        assert "401" in content

    def test_handle_authentication_error_should_have_correct_error_structure(self):
        """
        Given: Authentication error
        When: AuthPresenter.handle_authentication_error() is called
        Then: Should have correct JSON:API error fields
        """
        # When
        response = AuthPresenter.handle_authentication_error("Test error")
        content = response.body.decode("utf-8")

        # Then
        assert '"status":"401"' in content or '"status": "401"' in content
        assert (
            '"code":"AUTHENTICATION_FAILED"' in content
            or '"code": "AUTHENTICATION_FAILED"' in content
        )
        assert (
            '"title":"Authentication Failed"' in content
            or '"title": "Authentication Failed"' in content
        )
        assert '"/data/attributes/credentials"' in content


# ============================================================================
# AuthPresenter.handle_invalid_credentials Tests
# ============================================================================


class TestAuthPresenterHandleInvalidCredentials:
    """Tests for AuthPresenter.handle_invalid_credentials()."""

    def test_handle_invalid_credentials_should_return_400_jsonapi_error(self):
        """
        Given: Invalid credentials scenario
        When: AuthPresenter.handle_invalid_credentials() is called
        Then: Should return 400 JSONResponse with JSON:API error structure
        """
        # When
        response = AuthPresenter.handle_invalid_credentials()

        # Then
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        assert response.media_type == "application/vnd.api+json"

    def test_handle_invalid_credentials_should_have_generic_message(self):
        """
        Given: Invalid credentials scenario
        When: AuthPresenter.handle_invalid_credentials() is called
        Then: Should return generic error message for security
        """
        # When
        response = AuthPresenter.handle_invalid_credentials()
        content = response.body.decode("utf-8")

        # Then
        assert "Incorrect username or password" in content
        assert "INVALID_CREDENTIALS" in content

    def test_handle_invalid_credentials_should_have_correct_error_structure(self):
        """
        Given: Invalid credentials scenario
        When: AuthPresenter.handle_invalid_credentials() is called
        Then: Should have correct JSON:API error fields
        """
        # When
        response = AuthPresenter.handle_invalid_credentials()
        content = response.body.decode("utf-8")

        # Then
        assert '"status":"400"' in content or '"status": "400"' in content
        assert (
            '"code":"INVALID_CREDENTIALS"' in content
            or '"code": "INVALID_CREDENTIALS"' in content
        )
        assert (
            '"title":"Invalid Credentials"' in content
            or '"title": "Invalid Credentials"' in content
        )
        assert '"/data/attributes/credentials"' in content
