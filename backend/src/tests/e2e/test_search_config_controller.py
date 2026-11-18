"""
E2E Tests for SearchConfig Controller

Tests the complete search config flow:
    HTTP Request → SearchConfigController → SearchConfigUseCases → SearchConfigRepository → Database
"""

from src.app.infrastructure.database.models.search_config_source_website_model import (  # noqa: F401
    search_config_source_website,
)

SEARCH_CONFIG_TYPE = "search_config"  # Used in requests (validator enforces singular)
SEARCH_CONFIG_RESPONSE_TYPE = "search_configs"  # Used in responses (plural)


# JSON:API payload helpers
def make_create_payload(**overrides):
    attrs = {
        "search_term": "iPhone 13",
        "user_id": None,  # Must be set per test
        "is_active": True,
        "frequency_days": 1,
        "preferred_time": "00:00:00",
        "source_website_ids": [],
        **overrides,
    }
    return {"data": {"type": SEARCH_CONFIG_TYPE, "attributes": attrs}}


def make_update_payload(**overrides):
    attrs = {**overrides}
    return {"data": {"type": SEARCH_CONFIG_TYPE, "attributes": attrs}}


# ============================================================================
# POST /search-configs/
# ============================================================================


class TestSearchConfigCreate:
    """Tests for POST /search-configs/"""

    def test_create_search_config_successfully(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: Authenticated staff user and a valid payload
        When: POST /search-configs/ is called
        Then: Returns 201 with created record in JSON:API format
        """
        response = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id),
            headers=staff_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["type"] == SEARCH_CONFIG_RESPONSE_TYPE
        assert data["data"]["attributes"]["search_term"] == "iPhone 13"
        assert data["data"]["attributes"]["user_id"] == sample_user.id
        assert "id" in data["data"]

    def test_create_with_source_website_ids(
        self, client, staff_auth_headers, sample_user, sample_store, test_db
    ):
        """
        Given: Valid payload with existing source_website_ids
        When: POST /search-configs/
        Then: Returns 201 with source_website_ids in response
        """
        response = client.post(
            "/search-configs/",
            json=make_create_payload(
                user_id=sample_user.id,
                source_website_ids=[sample_store.id],
            ),
            headers=staff_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert sample_store.id in data["data"]["attributes"]["source_website_ids"]

    def test_create_with_invalid_type_returns_400(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: type='search_configs' (plural — wrong)
        When: POST /search-configs/
        Then: Returns 400
        """
        payload = make_create_payload(user_id=sample_user.id)
        payload["data"]["type"] = "search_configs"

        response = client.post(
            "/search-configs/",
            json=payload,
            headers=staff_auth_headers,
        )

        assert response.status_code == 400

    def test_create_with_missing_search_term_returns_422(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: search_term is empty
        When: POST /search-configs/
        Then: Returns 422
        """
        payload = make_create_payload(user_id=sample_user.id, search_term="")

        response = client.post(
            "/search-configs/",
            json=payload,
            headers=staff_auth_headers,
        )

        assert response.status_code == 422

    def test_create_with_nonexistent_source_website_returns_404(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: source_website_id that doesn't exist
        When: POST /search-configs/
        Then: Returns 404
        """
        response = client.post(
            "/search-configs/",
            json=make_create_payload(
                user_id=sample_user.id, source_website_ids=[99999]
            ),
            headers=staff_auth_headers,
        )

        assert response.status_code == 404

    def test_create_duplicate_search_term_for_same_user_returns_409(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: Same search_term already exists for this user
        When: POST /search-configs/ is called again
        Then: Returns 409
        """
        client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, search_term="iPhone 13"),
            headers=staff_auth_headers,
        )

        response = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, search_term="iPhone 13"),
            headers=staff_auth_headers,
        )

        assert response.status_code == 409

    def test_create_without_auth_returns_401_or_403(self, client, sample_user):
        """
        Given: No authentication token
        When: POST /search-configs/
        Then: Returns 401 or 403
        """
        response = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id),
        )

        assert response.status_code in (401, 403)

    def test_create_with_invalid_frequency_days_returns_422(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: frequency_days=0
        When: POST /search-configs/
        Then: Returns 422
        """
        response = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, frequency_days=0),
            headers=staff_auth_headers,
        )

        assert response.status_code == 422


# ============================================================================
# GET /search-configs/
# ============================================================================


class TestSearchConfigList:
    """Tests for GET /search-configs/"""

    def test_list_returns_empty_collection_when_no_configs(
        self, client, staff_auth_headers
    ):
        """
        Given: No search configs in database
        When: GET /search-configs/
        Then: Returns 200 with empty data list and total=0
        """
        response = client.get("/search-configs/", headers=staff_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0

    def test_list_returns_created_configs(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: Two search configs created
        When: GET /search-configs/
        Then: Returns 200 with both in data list
        """
        client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, search_term="iPhone"),
            headers=staff_auth_headers,
        )
        client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, search_term="Samsung"),
            headers=staff_auth_headers,
        )

        response = client.get("/search-configs/", headers=staff_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] == 2
        assert len(data["data"]) == 2

    def test_list_without_auth_returns_401_or_403(self, client):
        """
        Given: No authentication token
        When: GET /search-configs/
        Then: Returns 401 or 403
        """
        response = client.get("/search-configs/")

        assert response.status_code in (401, 403)


# ============================================================================
# GET /search-configs/user/{user_id}
# ============================================================================


class TestSearchConfigGetByUser:
    """Tests for GET /search-configs/user/{user_id}"""

    def test_get_by_user_returns_configs_for_user(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: Two configs for a specific user
        When: GET /search-configs/user/{user_id}
        Then: Returns 200 with both configs
        """
        client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, search_term="iPhone"),
            headers=staff_auth_headers,
        )
        client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, search_term="iPad"),
            headers=staff_auth_headers,
        )

        response = client.get(
            f"/search-configs/user/{sample_user.id}", headers=staff_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    def test_get_by_user_returns_empty_for_unknown_user(
        self, client, staff_auth_headers
    ):
        """
        Given: User with no configs
        When: GET /search-configs/user/{user_id}
        Then: Returns 200 with empty list
        """
        response = client.get("/search-configs/user/99999", headers=staff_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


# ============================================================================
# GET /search-configs/{id}
# ============================================================================


class TestSearchConfigGetById:
    """Tests for GET /search-configs/{id}"""

    def test_get_by_id_returns_config_when_found(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: An existing search config
        When: GET /search-configs/{id}
        Then: Returns 200 with the config
        """
        create_response = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id),
            headers=staff_auth_headers,
        )
        config_id = create_response.json()["data"]["id"]

        response = client.get(
            f"/search-configs/{config_id}", headers=staff_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == config_id
        assert data["data"]["type"] == SEARCH_CONFIG_RESPONSE_TYPE

    def test_get_by_id_returns_404_when_not_found(self, client, staff_auth_headers):
        """
        Given: Non-existent id
        When: GET /search-configs/{id}
        Then: Returns 404
        """
        response = client.get("/search-configs/99999", headers=staff_auth_headers)

        assert response.status_code == 404


# ============================================================================
# PUT /search-configs/{id}
# ============================================================================


class TestSearchConfigUpdate:
    """Tests for PUT /search-configs/{id}"""

    def test_update_search_config_successfully(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: An existing search config
        When: PUT /search-configs/{id} with valid data
        Then: Returns 200 with updated config
        """
        create_response = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, search_term="iPhone 13"),
            headers=staff_auth_headers,
        )
        config_id = create_response.json()["data"]["id"]

        response = client.put(
            f"/search-configs/{config_id}",
            json=make_update_payload(search_term="iPhone 14", frequency_days=7),
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["attributes"]["search_term"] == "iPhone 14"
        assert data["data"]["attributes"]["frequency_days"] == 7

    def test_update_nonexistent_config_returns_404(self, client, staff_auth_headers):
        """
        Given: Non-existent id
        When: PUT /search-configs/{id}
        Then: Returns 404
        """
        response = client.put(
            "/search-configs/99999",
            json=make_update_payload(search_term="Something"),
            headers=staff_auth_headers,
        )

        assert response.status_code == 404

    def test_update_with_invalid_type_returns_400(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: type != 'search_config'
        When: PUT /search-configs/{id}
        Then: Returns 400
        """
        create_response = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id),
            headers=staff_auth_headers,
        )
        config_id = create_response.json()["data"]["id"]

        payload = make_update_payload(search_term="New term")
        payload["data"]["type"] = "wrong_type"

        response = client.put(
            f"/search-configs/{config_id}",
            json=payload,
            headers=staff_auth_headers,
        )

        assert response.status_code == 400

    def test_update_with_duplicate_term_for_same_user_returns_409(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: Two configs, updating first to have same term as second
        When: PUT /search-configs/{id}
        Then: Returns 409
        """
        r1 = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, search_term="iPhone"),
            headers=staff_auth_headers,
        )
        client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id, search_term="Samsung"),
            headers=staff_auth_headers,
        )
        config_id = r1.json()["data"]["id"]

        response = client.put(
            f"/search-configs/{config_id}",
            json=make_update_payload(search_term="Samsung"),
            headers=staff_auth_headers,
        )

        assert response.status_code == 409

    def test_update_without_auth_returns_401_or_403(self, client):
        """
        Given: No authentication
        When: PUT /search-configs/{id}
        Then: Returns 401 or 403
        """
        response = client.put(
            "/search-configs/1",
            json=make_update_payload(search_term="X"),
        )

        assert response.status_code in (401, 403)


# ============================================================================
# DELETE /search-configs/{id}
# ============================================================================


class TestSearchConfigDelete:
    """Tests for DELETE /search-configs/{id}"""

    def test_delete_search_config_returns_204(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: An existing search config
        When: DELETE /search-configs/{id}
        Then: Returns 204
        """
        create_response = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id),
            headers=staff_auth_headers,
        )
        config_id = create_response.json()["data"]["id"]

        response = client.delete(
            f"/search-configs/{config_id}", headers=staff_auth_headers
        )

        assert response.status_code == 204

    def test_delete_removes_config_from_database(
        self, client, staff_auth_headers, sample_user
    ):
        """
        Given: An existing search config
        When: DELETE /search-configs/{id} then GET the same id
        Then: GET returns 404
        """
        create_response = client.post(
            "/search-configs/",
            json=make_create_payload(user_id=sample_user.id),
            headers=staff_auth_headers,
        )
        config_id = create_response.json()["data"]["id"]

        client.delete(f"/search-configs/{config_id}", headers=staff_auth_headers)

        get_response = client.get(
            f"/search-configs/{config_id}", headers=staff_auth_headers
        )
        assert get_response.status_code == 404

    def test_delete_nonexistent_config_returns_404(self, client, staff_auth_headers):
        """
        Given: Non-existent id
        When: DELETE /search-configs/{id}
        Then: Returns 404
        """
        response = client.delete("/search-configs/99999", headers=staff_auth_headers)

        assert response.status_code == 404

    def test_delete_without_auth_returns_401_or_403(self, client):
        """
        Given: No authentication
        When: DELETE /search-configs/{id}
        Then: Returns 401 or 403
        """
        response = client.delete("/search-configs/1")

        assert response.status_code in (401, 403)
