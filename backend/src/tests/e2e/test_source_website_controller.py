"""
E2E Tests for SourceWebsite Controller

Tests the complete source website management flow:
    HTTP Request → SourceWebsiteController → SourceWebsiteUseCases → StoreRepository → Database
"""

from src.app.stores.persistence.models import Store as StoreModel

SOURCE_WEBSITE_TYPE = "source_website"  # Used in requests (validator enforces singular)
SOURCE_WEBSITE_RESPONSE_TYPE = (
    "source_websites"  # Used in responses (schema returns plural)
)


# JSON:API payload helpers
def make_create_payload(**overrides):
    attrs = {
        "name": "OLX",
        "base_url": "https://www.olx.com.br",
        "is_active": True,
        **overrides,
    }
    return {"data": {"type": SOURCE_WEBSITE_TYPE, "attributes": attrs}}


def make_update_payload(**overrides):
    return {"data": {"type": SOURCE_WEBSITE_TYPE, "attributes": overrides}}


# ============================================================================
# POST /source-websites/
# ============================================================================


class TestSourceWebsiteCreate:
    """Tests for POST /source-websites/ - Create new source website"""

    def test_create_source_website_successfully(self, client, staff_auth_headers):
        """
        Given: Authenticated staff user
        When: POST /source-websites/ with valid data in JSON:API format
        Then: Returns 201 with created source website in JSON:API format
        """
        response = client.post(
            "/source-websites/",
            json=make_create_payload(),
            headers=staff_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["type"] == SOURCE_WEBSITE_RESPONSE_TYPE
        assert data["data"]["attributes"]["name"] == "OLX"
        assert data["data"]["attributes"]["base_url"] == "https://www.olx.com.br"
        assert "id" in data["data"]

    def test_create_source_website_with_duplicate_name_returns_409(
        self, client, staff_auth_headers, sample_source_website
    ):
        """
        Given: A source website with the given name already exists
        When: POST /source-websites/ with the same name
        Then: Returns 409 (Conflict)
        """
        response = client.post(
            "/source-websites/",
            json=make_create_payload(name=sample_source_website.name),
            headers=staff_auth_headers,
        )

        assert response.status_code == 409

    def test_create_source_website_with_invalid_type_returns_400(
        self, client, staff_auth_headers
    ):
        """
        Given: Authenticated staff user
        When: POST /source-websites/ with wrong JSON:API type
        Then: Returns 400 (Bad Request)
        """
        payload = {
            "data": {
                "type": "source_websites",  # Must be singular
                "attributes": {"name": "OLX", "base_url": "https://www.olx.com.br"},
            }
        }

        response = client.post(
            "/source-websites/",
            json=payload,
            headers=staff_auth_headers,
        )

        assert response.status_code == 400

    def test_create_source_website_missing_required_fields_returns_422(
        self, client, staff_auth_headers
    ):
        """
        Given: Authenticated staff user
        When: POST /source-websites/ missing required fields (name, base_url)
        Then: Returns 422 (Unprocessable Entity)
        """
        payload = {"data": {"type": SOURCE_WEBSITE_TYPE, "attributes": {}}}

        response = client.post(
            "/source-websites/",
            json=payload,
            headers=staff_auth_headers,
        )

        assert response.status_code == 422

    def test_create_source_website_without_auth_returns_401(self, client):
        """
        Given: No authentication token
        When: POST /source-websites/ with valid data
        Then: Returns 401 or 403 (Unauthorized/Forbidden)
        """
        response = client.post(
            "/source-websites/",
            json=make_create_payload(),
        )

        assert response.status_code in (401, 403)


# ============================================================================
# GET /source-websites/
# ============================================================================


class TestSourceWebsiteList:
    """Tests for GET /source-websites/ - List source websites"""

    def test_list_source_websites_returns_collection(
        self, client, staff_auth_headers, sample_source_website
    ):
        """
        Given: A source website exists in the database
        When: GET /source-websites/
        Then: Returns 200 with collection containing the source website
        """
        response = client.get("/source-websites/", headers=staff_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1

    def test_list_source_websites_empty_returns_empty_collection(
        self, client, staff_auth_headers
    ):
        """
        Given: No source websites in the database
        When: GET /source-websites/
        Then: Returns 200 with empty list
        """
        response = client.get("/source-websites/", headers=staff_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    def test_list_source_websites_supports_pagination(
        self, client, staff_auth_headers, test_db
    ):
        """
        Given: Multiple source websites exist
        When: GET /source-websites/?limit=1&offset=0
        Then: Returns only 1 result
        """
        for name, url in [
            ("Site A", "https://site-a.com"),
            ("Site B", "https://site-b.com"),
        ]:
            test_db.add(StoreModel(name=name, base_url=url, is_active=True))
        test_db.commit()

        response = client.get(
            "/source-websites/?limit=1&offset=0",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    def test_list_source_websites_without_auth_returns_401(self, client):
        """
        Given: No authentication token
        When: GET /source-websites/
        Then: Returns 401 or 403 (Unauthorized/Forbidden)
        """
        response = client.get("/source-websites/")

        assert response.status_code in (401, 403)


# ============================================================================
# GET /source-websites/{id}
# ============================================================================


class TestSourceWebsiteGetById:
    """Tests for GET /source-websites/{id} - Get source website by ID"""

    def test_get_source_website_by_id_found_returns_200(
        self, client, staff_auth_headers, sample_source_website
    ):
        """
        Given: A source website exists with a known ID
        When: GET /source-websites/{id}
        Then: Returns 200 with the source website
        """
        response = client.get(
            f"/source-websites/{sample_source_website.id}",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["type"] == SOURCE_WEBSITE_RESPONSE_TYPE
        assert data["data"]["id"] == str(sample_source_website.id)
        assert data["data"]["attributes"]["name"] == sample_source_website.name

    def test_get_source_website_by_id_not_found_returns_404(
        self, client, staff_auth_headers
    ):
        """
        Given: No source website with the given ID exists
        When: GET /source-websites/99999
        Then: Returns 404 (Not Found)
        """
        response = client.get("/source-websites/99999", headers=staff_auth_headers)

        assert response.status_code == 404

    def test_get_source_website_by_id_without_auth_returns_401(
        self, client, sample_source_website
    ):
        """
        Given: No authentication token
        When: GET /source-websites/{id}
        Then: Returns 401 or 403 (Unauthorized/Forbidden)
        """
        response = client.get(f"/source-websites/{sample_source_website.id}")

        assert response.status_code in (401, 403)


# ============================================================================
# GET /source-websites/name/{name}
# ============================================================================


class TestSourceWebsiteGetByName:
    """Tests for GET /source-websites/name/{name} - Get source website by name"""

    def test_get_source_website_by_name_found_returns_200(
        self, client, staff_auth_headers, sample_source_website
    ):
        """
        Given: A source website exists with a known name
        When: GET /source-websites/name/{name}
        Then: Returns 200 with the source website
        """
        response = client.get(
            f"/source-websites/name/{sample_source_website.name}",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["attributes"]["name"] == sample_source_website.name

    def test_get_source_website_by_name_not_found_returns_404(
        self, client, staff_auth_headers
    ):
        """
        Given: No source website with the given name exists
        When: GET /source-websites/name/DoesNotExist
        Then: Returns 404 (Not Found)
        """
        response = client.get(
            "/source-websites/name/DoesNotExist", headers=staff_auth_headers
        )

        assert response.status_code == 404

    def test_get_source_website_by_name_without_auth_returns_401(
        self, client, sample_source_website
    ):
        """
        Given: No authentication token
        When: GET /source-websites/name/{name}
        Then: Returns 401 or 403 (Unauthorized/Forbidden)
        """
        response = client.get(f"/source-websites/name/{sample_source_website.name}")

        assert response.status_code in (401, 403)


# ============================================================================
# PUT /source-websites/{id}
# ============================================================================


class TestSourceWebsiteUpdate:
    """Tests for PUT /source-websites/{id} - Update source website"""

    def test_update_source_website_successfully(
        self, client, staff_auth_headers, sample_source_website
    ):
        """
        Given: A source website exists
        When: PUT /source-websites/{id} with updated name
        Then: Returns 200 with updated source website
        """
        response = client.put(
            f"/source-websites/{sample_source_website.id}",
            json=make_update_payload(name="Updated Name"),
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["attributes"]["name"] == "Updated Name"

    def test_update_source_website_not_found_returns_404(
        self, client, staff_auth_headers
    ):
        """
        Given: No source website with the given ID exists
        When: PUT /source-websites/99999
        Then: Returns 404 (Not Found)
        """
        response = client.put(
            "/source-websites/99999",
            json=make_update_payload(name="Anything"),
            headers=staff_auth_headers,
        )

        assert response.status_code == 404

    def test_update_source_website_with_duplicate_name_returns_409(
        self, client, staff_auth_headers, sample_source_website, test_db
    ):
        """
        Given: Two source websites exist
        When: PUT with the name of the other source website
        Then: Returns 409 (Conflict)
        """
        other = StoreModel(
            name="OtherSite", base_url="https://other.com", is_active=True
        )
        test_db.add(other)
        test_db.commit()
        test_db.refresh(other)

        response = client.put(
            f"/source-websites/{sample_source_website.id}",
            json=make_update_payload(name="OtherSite"),
            headers=staff_auth_headers,
        )

        assert response.status_code == 409

    def test_update_source_website_without_auth_returns_401(
        self, client, sample_source_website
    ):
        """
        Given: No authentication token
        When: PUT /source-websites/{id}
        Then: Returns 401 or 403 (Unauthorized/Forbidden)
        """
        response = client.put(
            f"/source-websites/{sample_source_website.id}",
            json=make_update_payload(name="No Auth"),
        )

        assert response.status_code in (401, 403)


# ============================================================================
# DELETE /source-websites/{id}
# ============================================================================


class TestSourceWebsiteDelete:
    """Tests for DELETE /source-websites/{id} - Delete source website"""

    def test_delete_source_website_successfully(
        self, client, staff_auth_headers, sample_source_website
    ):
        """
        Given: A source website exists
        When: DELETE /source-websites/{id}
        Then: Returns 204 and source website is no longer retrievable
        """
        response = client.delete(
            f"/source-websites/{sample_source_website.id}",
            headers=staff_auth_headers,
        )

        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(
            f"/source-websites/{sample_source_website.id}",
            headers=staff_auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_source_website_not_found_returns_404(
        self, client, staff_auth_headers
    ):
        """
        Given: No source website with the given ID exists
        When: DELETE /source-websites/99999
        Then: Returns 404 (Not Found)
        """
        response = client.delete("/source-websites/99999", headers=staff_auth_headers)

        assert response.status_code == 404

    def test_delete_source_website_without_auth_returns_401(
        self, client, sample_source_website
    ):
        """
        Given: No authentication token
        When: DELETE /source-websites/{id}
        Then: Returns 401 or 403 (Unauthorized/Forbidden)
        """
        response = client.delete(f"/source-websites/{sample_source_website.id}")

        assert response.status_code in (401, 403)
