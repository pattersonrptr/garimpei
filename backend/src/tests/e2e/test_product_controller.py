"""
E2E Tests for Product Controller

Tests the complete product management flow:
    HTTP Request → ProductController → ProductUseCases → ProductRepository → Database
"""

PRODUCT_TYPE = "product"  # Used in requests (validator enforces singular)
PRODUCT_RESPONSE_TYPE = "products"  # Used in responses (schema returns plural)


# JSON:API payload helpers
def make_create_payload(**overrides):
    attrs = {
        "url": "https://test.example.com/product/new",
        "title": "New Product",
        "condition": "new",
        "is_available": True,
        **overrides,
    }
    return {"data": {"type": PRODUCT_TYPE, "attributes": attrs}}


def make_update_payload(**overrides):
    return {"data": {"type": PRODUCT_TYPE, "attributes": overrides}}


# ============================================================================
# POST /products/
# ============================================================================


class TestProductCreate:
    """Test POST /products/ - Create new product"""

    def test_create_product_successfully(
        self, client, staff_auth_headers, sample_store
    ):
        """
        Given: Authenticated staff user and an existing source website
        When: POST /products/ with valid product data in JSON:API format
        Then: Returns 201 with created product in JSON:API format
        """
        # When
        response = client.post(
            "/products/",
            json=make_create_payload(source_website_id=sample_store.id),
            headers=staff_auth_headers,
        )

        # Then
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["type"] == PRODUCT_RESPONSE_TYPE
        assert data["data"]["attributes"]["title"] == "New Product"
        assert (
            data["data"]["attributes"]["url"] == "https://test.example.com/product/new"
        )
        assert "id" in data["data"]

    def test_create_product_with_duplicate_url(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: A product with a given URL already exists
        When: POST /products/ with the same URL
        Then: Returns 409 (Conflict) with validation error
        """
        # When
        response = client.post(
            "/products/",
            json=make_create_payload(
                url=sample_product.url,
                source_website_id=sample_product.source_website_id,
            ),
            headers=staff_auth_headers,
        )

        # Then
        assert response.status_code == 409
        data = response.json()
        assert "errors" in data
        assert any("url" in err["detail"].lower() for err in data["errors"])

    def test_create_product_with_invalid_condition(
        self, client, staff_auth_headers, sample_store
    ):
        """
        Given: Authenticated staff user
        When: POST /products/ with an invalid enum value for condition
        Then: Returns 422 (Unprocessable Entity)
        """
        # When
        response = client.post(
            "/products/",
            json=make_create_payload(
                condition="not_a_valid_condition",
                source_website_id=sample_store.id,
            ),
            headers=staff_auth_headers,
        )

        # Then
        assert response.status_code == 422

    def test_create_product_missing_required_fields(self, client, staff_auth_headers):
        """
        Given: Authenticated staff user
        When: POST /products/ without required fields (url, title, source_website_id)
        Then: Returns 422 (Unprocessable Entity)
        """
        # When
        response = client.post(
            "/products/",
            json={"data": {"type": PRODUCT_TYPE, "attributes": {}}},
            headers=staff_auth_headers,
        )

        # Then
        assert response.status_code == 422

    def test_create_product_without_authentication(self, client, sample_store):
        """
        Given: No authentication token
        When: POST /products/ without auth headers
        Then: Returns 401 or 403 (unauthorized)
        """
        # When
        response = client.post(
            "/products/",
            json=make_create_payload(source_website_id=sample_store.id),
        )

        # Then
        assert response.status_code in (401, 403)

    def test_create_product_with_regular_user_is_forbidden(
        self, client, auth_headers, sample_store
    ):
        """
        Given: Authenticated regular user (not staff, not superuser)
        When: POST /products/ with valid data
        Then: Returns 403 (Forbidden)
        """
        # When
        response = client.post(
            "/products/",
            json=make_create_payload(source_website_id=sample_store.id),
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 403


# ============================================================================
# GET /products/
# ============================================================================


class TestProductList:
    """Test GET /products/ - List all products"""

    def test_list_products_returns_collection(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: An existing product and authenticated staff user
        When: GET /products/
        Then: Returns 200 with products collection and meta.total
        """
        # When
        response = client.get("/products/", headers=staff_auth_headers)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
        assert data["meta"]["total"] >= 1

    def test_list_products_empty_when_none_exist(self, client, staff_auth_headers):
        """
        Given: No products exist and authenticated staff user
        When: GET /products/
        Then: Returns 200 with empty list and total=0
        """
        # When
        response = client.get("/products/", headers=staff_auth_headers)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0

    def test_list_products_with_pagination(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: An existing product and authenticated staff user
        When: GET /products/?limit=1&offset=0
        Then: Returns 200 with at most 1 product
        """
        # When
        response = client.get("/products/?limit=1&offset=0", headers=staff_auth_headers)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 1

    def test_list_products_without_authentication(self, client):
        """
        Given: No authentication token
        When: GET /products/
        Then: Returns 401 or 403
        """
        # When
        response = client.get("/products/")

        # Then
        assert response.status_code in (401, 403)


# ============================================================================
# GET /products/{id}
# ============================================================================


class TestProductGetById:
    """Test GET /products/{id} - Get product by ID"""

    def test_get_product_by_id_returns_product(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: An existing product and authenticated staff user
        When: GET /products/{id} with a valid existing ID
        Then: Returns 200 with the product in JSON:API format
        """
        # When
        response = client.get(
            f"/products/{sample_product.id}", headers=staff_auth_headers
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["type"] == PRODUCT_RESPONSE_TYPE
        assert data["data"]["id"] == str(sample_product.id)
        assert data["data"]["attributes"]["title"] == sample_product.title

    def test_get_product_by_id_not_found(self, client, staff_auth_headers):
        """
        Given: No product with ID 99999 exists and authenticated staff user
        When: GET /products/99999
        Then: Returns 404 with error
        """
        # When
        response = client.get("/products/99999", headers=staff_auth_headers)

        # Then
        assert response.status_code == 404
        data = response.json()
        assert "errors" in data

    def test_get_product_by_id_without_authentication(self, client, sample_product):
        """
        Given: No authentication token
        When: GET /products/{id}
        Then: Returns 401 or 403
        """
        # When
        response = client.get(f"/products/{sample_product.id}")

        # Then
        assert response.status_code in (401, 403)


# ============================================================================
# GET /products/url?url=...
# ============================================================================


class TestProductGetByUrl:
    """Test GET /products/url?url=... - Get product by URL"""

    def test_get_product_by_url_returns_product(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: An existing product and authenticated staff user
        When: GET /products/url?url=<existing_url>
        Then: Returns 200 with the matching product
        """
        # When
        response = client.get(
            f"/products/url?url={sample_product.url}", headers=staff_auth_headers
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["attributes"]["url"] == sample_product.url

    def test_get_product_by_url_not_found(self, client, staff_auth_headers):
        """
        Given: No product with the given URL exists and authenticated staff user
        When: GET /products/url?url=https://nonexistent.example.com/product
        Then: Returns 404 with error
        """
        # When
        response = client.get(
            "/products/url?url=https://nonexistent.example.com/product",
            headers=staff_auth_headers,
        )

        # Then
        assert response.status_code == 404
        data = response.json()
        assert "errors" in data

    def test_get_product_by_url_without_authentication(self, client, sample_product):
        """
        Given: No authentication token
        When: GET /products/url?url=...
        Then: Returns 401 or 403
        """
        # When
        response = client.get(f"/products/url?url={sample_product.url}")

        # Then
        assert response.status_code in (401, 403)


# ============================================================================
# PUT /products/{id}
# ============================================================================


class TestProductUpdate:
    """Test PUT /products/{id} - Update a product"""

    def test_update_product_successfully(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: An existing product and authenticated staff user
        When: PUT /products/{id} with updated title
        Then: Returns 200 with updated product data
        """
        # When
        response = client.put(
            f"/products/{sample_product.id}",
            json=make_update_payload(title="Updated Title"),
            headers=staff_auth_headers,
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["attributes"]["title"] == "Updated Title"

    def test_update_product_not_found(self, client, staff_auth_headers):
        """
        Given: No product with ID 99999 exists and authenticated staff user
        When: PUT /products/99999 with update data
        Then: Returns 404 with error
        """
        # When
        response = client.put(
            "/products/99999",
            json=make_update_payload(title="Won't Work"),
            headers=staff_auth_headers,
        )

        # Then
        assert response.status_code == 404
        data = response.json()
        assert "errors" in data

    def test_update_product_with_duplicate_url(
        self, client, staff_auth_headers, sample_product, sample_store
    ):
        """
        Given: Two products exist — sample_product and a second one
        When: PUT on the second product using the URL already taken by sample_product
        Then: Returns 409 (Conflict)
        """
        # Create a second product via the API
        response_create = client.post(
            "/products/",
            json=make_create_payload(
                url="https://test.example.com/product/second",
                title="Second Product",
                condition="used",
                source_website_id=sample_store.id,
            ),
            headers=staff_auth_headers,
        )
        assert response_create.status_code == 201
        second_id = response_create.json()["data"]["id"]

        # Now try to update second product to use first product's URL
        response = client.put(
            f"/products/{second_id}",
            json=make_update_payload(url=sample_product.url),
            headers=staff_auth_headers,
        )

        # Then
        assert response.status_code == 409
        data = response.json()
        assert "errors" in data

    def test_update_product_without_authentication(self, client, sample_product):
        """
        Given: No authentication token
        When: PUT /products/{id}
        Then: Returns 401 or 403
        """
        # When
        response = client.put(
            f"/products/{sample_product.id}",
            json=make_update_payload(title="No Auth"),
        )

        # Then
        assert response.status_code in (401, 403)


# ============================================================================
# DELETE /products/{id}
# ============================================================================


class TestProductDelete:
    """Test DELETE /products/{id} - Delete a product"""

    def test_delete_product_successfully(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: An existing product and authenticated staff user
        When: DELETE /products/{id}
        Then: Returns 204 (No Content)
        """
        # When
        response = client.delete(
            f"/products/{sample_product.id}", headers=staff_auth_headers
        )

        # Then
        assert response.status_code == 204

        # And: Product is no longer retrievable
        get_response = client.get(
            f"/products/{sample_product.id}", headers=staff_auth_headers
        )
        assert get_response.status_code == 404

    def test_delete_product_not_found(self, client, staff_auth_headers):
        """
        Given: No product with ID 99999 exists and authenticated staff user
        When: DELETE /products/99999
        Then: Returns 404 with error
        """
        # When
        response = client.delete("/products/99999", headers=staff_auth_headers)

        # Then
        assert response.status_code == 404
        data = response.json()
        assert "errors" in data

    def test_delete_product_without_authentication(self, client, sample_product):
        """
        Given: No authentication token
        When: DELETE /products/{id}
        Then: Returns 401 or 403
        """
        # When
        response = client.delete(f"/products/{sample_product.id}")

        # Then
        assert response.status_code in (401, 403)
