"""
E2E Tests for PriceHistory Controller

Tests the complete price history flow:
    HTTP Request → PriceHistoryController → PriceHistoryUseCases → PriceHistoryRepository → Database
"""

from src.app.catalog.persistence.models import (
    PriceHistory as PriceHistoryModel,
)

PRICE_HISTORY_TYPE = "price_history"  # Used in requests (validator enforces singular)
PRICE_HISTORY_RESPONSE_TYPE = "price_histories"  # Used in responses (plural)


# JSON:API payload helper
def make_create_payload(**overrides):
    attrs = {"product_id": None, "price": 999.90, **overrides}
    return {"data": {"type": PRICE_HISTORY_TYPE, "attributes": attrs}}


# ============================================================================
# POST /price-histories/
# ============================================================================


class TestPriceHistoryCreate:
    """Tests for POST /price-histories/"""

    def test_create_price_history_successfully(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: Authenticated staff user and an existing product
        When: POST /price-histories/ with valid data
        Then: Returns 201 with created record in JSON:API format
        """
        response = client.post(
            "/price-histories/",
            json=make_create_payload(product_id=sample_product.id),
            headers=staff_auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["type"] == PRICE_HISTORY_RESPONSE_TYPE
        assert data["data"]["attributes"]["price"] == 999.90
        assert data["data"]["attributes"]["product_id"] == sample_product.id
        assert "id" in data["data"]

    def test_create_price_history_with_nonexistent_product_returns_404(
        self, client, staff_auth_headers
    ):
        """
        Given: product_id does not exist
        When: POST /price-histories/
        Then: Returns 404
        """
        response = client.post(
            "/price-histories/",
            json=make_create_payload(product_id=99999),
            headers=staff_auth_headers,
        )

        assert response.status_code == 404

    def test_create_price_history_with_invalid_type_returns_400(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: type='price_histories' (plural — wrong)
        When: POST /price-histories/
        Then: Returns 400
        """
        payload = {
            "data": {
                "type": "price_histories",
                "attributes": {"product_id": sample_product.id, "price": 100.0},
            }
        }
        response = client.post(
            "/price-histories/",
            json=payload,
            headers=staff_auth_headers,
        )

        assert response.status_code == 400

    def test_create_price_history_with_invalid_price_returns_422(
        self, client, staff_auth_headers, sample_product
    ):
        """
        Given: price=0 (invalid)
        When: POST /price-histories/
        Then: Returns 422
        """
        response = client.post(
            "/price-histories/",
            json=make_create_payload(product_id=sample_product.id, price=0),
            headers=staff_auth_headers,
        )

        assert response.status_code == 422

    def test_create_price_history_without_auth_returns_401_or_403(
        self, client, sample_product
    ):
        """
        Given: No authentication token
        When: POST /price-histories/
        Then: Returns 401 or 403
        """
        response = client.post(
            "/price-histories/",
            json=make_create_payload(product_id=sample_product.id),
        )

        assert response.status_code in (401, 403)


# ============================================================================
# GET /price-histories/
# ============================================================================


class TestPriceHistoryList:
    """Tests for GET /price-histories/"""

    def test_list_price_histories_returns_collection(
        self, client, staff_auth_headers, test_db, sample_product
    ):
        """
        Given: A price history record exists
        When: GET /price-histories/
        Then: Returns 200 with collection
        """
        test_db.add(PriceHistoryModel(product_id=sample_product.id, price=500.0))
        test_db.commit()

        response = client.get("/price-histories/", headers=staff_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1

    def test_list_price_histories_empty_returns_empty_collection(
        self, client, staff_auth_headers
    ):
        response = client.get("/price-histories/", headers=staff_auth_headers)

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_list_price_histories_supports_pagination(
        self, client, staff_auth_headers, test_db, sample_product
    ):
        for price in [100.0, 200.0, 300.0]:
            test_db.add(PriceHistoryModel(product_id=sample_product.id, price=price))
        test_db.commit()

        response = client.get(
            "/price-histories/?limit=2&offset=0", headers=staff_auth_headers
        )

        assert response.status_code == 200
        assert len(response.json()["data"]) == 2

    def test_list_price_histories_without_auth_returns_401_or_403(self, client):
        response = client.get("/price-histories/")
        assert response.status_code in (401, 403)


# ============================================================================
# GET /price-histories/{id}
# ============================================================================


class TestPriceHistoryGetById:
    """Tests for GET /price-histories/{id}"""

    def test_get_by_id_found_returns_200(
        self, client, staff_auth_headers, test_db, sample_product
    ):
        record = PriceHistoryModel(product_id=sample_product.id, price=750.0)
        test_db.add(record)
        test_db.commit()
        test_db.refresh(record)

        response = client.get(
            f"/price-histories/{record.id}", headers=staff_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["type"] == PRICE_HISTORY_RESPONSE_TYPE
        assert data["data"]["id"] == str(record.id)

    def test_get_by_id_not_found_returns_404(self, client, staff_auth_headers):
        response = client.get("/price-histories/99999", headers=staff_auth_headers)
        assert response.status_code == 404

    def test_get_by_id_without_auth_returns_401_or_403(
        self, client, test_db, sample_product
    ):
        record = PriceHistoryModel(product_id=sample_product.id, price=750.0)
        test_db.add(record)
        test_db.commit()
        test_db.refresh(record)

        response = client.get(f"/price-histories/{record.id}")
        assert response.status_code in (401, 403)


# ============================================================================
# GET /price-histories/product/{product_id}
# ============================================================================


class TestPriceHistoryGetByProduct:
    """Tests for GET /price-histories/product/{product_id}"""

    def test_get_by_product_id_returns_all_records(
        self, client, staff_auth_headers, test_db, sample_product
    ):
        for price in [100.0, 200.0]:
            test_db.add(PriceHistoryModel(product_id=sample_product.id, price=price))
        test_db.commit()

        response = client.get(
            f"/price-histories/product/{sample_product.id}",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    def test_get_by_product_id_with_no_records_returns_empty_collection(
        self, client, staff_auth_headers
    ):
        response = client.get(
            "/price-histories/product/99999", headers=staff_auth_headers
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_get_by_product_without_auth_returns_401_or_403(
        self, client, sample_product
    ):
        response = client.get(f"/price-histories/product/{sample_product.id}")
        assert response.status_code in (401, 403)


# ============================================================================
# GET /price-histories/product/{product_id}/latest
# ============================================================================


class TestPriceHistoryGetLatestByProduct:
    """Tests for GET /price-histories/product/{product_id}/latest"""

    def test_get_latest_returns_200_with_record(
        self, client, staff_auth_headers, test_db, sample_product
    ):
        test_db.add(PriceHistoryModel(product_id=sample_product.id, price=800.0))
        test_db.commit()

        response = client.get(
            f"/price-histories/product/{sample_product.id}/latest",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["data"]["attributes"]["price"] == 800.0

    def test_get_latest_with_no_records_returns_404(self, client, staff_auth_headers):
        response = client.get(
            "/price-histories/product/99999/latest",
            headers=staff_auth_headers,
        )
        assert response.status_code == 404

    def test_get_latest_without_auth_returns_401_or_403(self, client, sample_product):
        response = client.get(f"/price-histories/product/{sample_product.id}/latest")
        assert response.status_code in (401, 403)


# ============================================================================
# DELETE /price-histories/{id}
# ============================================================================


class TestPriceHistoryDelete:
    """Tests for DELETE /price-histories/{id}"""

    def test_delete_successfully_returns_204_and_record_is_gone(
        self, client, staff_auth_headers, test_db, sample_product
    ):
        record = PriceHistoryModel(product_id=sample_product.id, price=500.0)
        test_db.add(record)
        test_db.commit()
        test_db.refresh(record)

        response = client.delete(
            f"/price-histories/{record.id}", headers=staff_auth_headers
        )
        assert response.status_code == 204

        get_response = client.get(
            f"/price-histories/{record.id}", headers=staff_auth_headers
        )
        assert get_response.status_code == 404

    def test_delete_not_found_returns_404(self, client, staff_auth_headers):
        response = client.delete("/price-histories/99999", headers=staff_auth_headers)
        assert response.status_code == 404

    def test_delete_without_auth_returns_401_or_403(
        self, client, test_db, sample_product
    ):
        record = PriceHistoryModel(product_id=sample_product.id, price=500.0)
        test_db.add(record)
        test_db.commit()
        test_db.refresh(record)

        response = client.delete(f"/price-histories/{record.id}")
        assert response.status_code in (401, 403)
