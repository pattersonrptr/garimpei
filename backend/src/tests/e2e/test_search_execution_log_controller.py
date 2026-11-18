"""
E2E Tests for SearchExecutionLog Controller (read-only)

Tests the complete read flow:
    HTTP Request → SearchExecutionLogController → UseCases → Repository → Database

Note: SearchExecutionLogs are created internally by the system (scrapers/Celery),
      not via HTTP. The controller exposes only GET endpoints.
"""

RESPONSE_TYPE = "search_execution_logs"


# ============================================================================
# GET /search-execution-logs/
# ============================================================================


class TestListSearchExecutionLogs:
    """Tests for GET /search-execution-logs/"""

    def test_list_returns_200_with_empty_collection(self, client, staff_auth_headers):
        """
        Given: No logs in database
        When: GET /search-execution-logs/
        Then: Returns 200 with empty data array and meta.total=0
        """
        response = client.get(
            "/search-execution-logs/",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0

    def test_list_returns_existing_logs(
        self, client, staff_auth_headers, sample_search_execution_log
    ):
        """
        Given: One log exists in database
        When: GET /search-execution-logs/
        Then: Returns 200 with one item, correct type and attributes
        """
        response = client.get(
            "/search-execution-logs/",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] == 1
        assert data["data"][0]["type"] == RESPONSE_TYPE
        assert data["data"][0]["attributes"]["status"] == "success"
        assert data["data"][0]["attributes"]["results_count"] == 3

    def test_list_pagination_limit_and_offset(
        self, client, staff_auth_headers, test_db, sample_search_config
    ):
        """
        Given: 5 logs in database
        When: GET /search-execution-logs/?limit=2&offset=2
        Then: Returns 2 items, total=5
        """
        from src.app.searches.persistence.models import SearchRun as SearchRunModel

        for _ in range(5):
            log = SearchRunModel(
                search_config_id=sample_search_config.id, status="pending"
            )
            test_db.add(log)
        test_db.commit()

        response = client.get(
            "/search-execution-logs/?limit=2&offset=2",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] == 5
        assert len(data["data"]) == 2

    def test_list_without_auth_returns_401_or_403(self, client):
        """
        Given: No authentication token
        When: GET /search-execution-logs/
        Then: Returns 401 or 403
        """
        response = client.get("/search-execution-logs/")
        assert response.status_code in (401, 403)


# ============================================================================
# GET /search-execution-logs/search-config/{search_config_id}
# ============================================================================


class TestGetSearchExecutionLogsBySearchConfig:
    """Tests for GET /search-execution-logs/search-config/{search_config_id}"""

    def test_get_by_search_config_returns_logs(
        self,
        client,
        staff_auth_headers,
        sample_search_execution_log,
        sample_search_config,
    ):
        """
        Given: One log exists for a search config
        When: GET /search-execution-logs/search-config/{id}
        Then: Returns 200 with that log
        """
        response = client.get(
            f"/search-execution-logs/search-config/{sample_search_config.id}",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] == 1
        assert (
            data["data"][0]["attributes"]["search_config_id"] == sample_search_config.id
        )

    def test_get_by_nonexistent_search_config_returns_empty_list(
        self, client, staff_auth_headers
    ):
        """
        Given: No logs for search_config_id=99999
        When: GET /search-execution-logs/search-config/99999
        Then: Returns 200 with empty data array
        """
        response = client.get(
            "/search-execution-logs/search-config/99999",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0

    def test_get_by_search_config_without_auth_returns_401_or_403(self, client):
        """
        Given: No authentication token
        When: GET /search-execution-logs/search-config/1
        Then: Returns 401 or 403
        """
        response = client.get("/search-execution-logs/search-config/1")
        assert response.status_code in (401, 403)


# ============================================================================
# GET /search-execution-logs/{id}
# ============================================================================


class TestGetSearchExecutionLogById:
    """Tests for GET /search-execution-logs/{id}"""

    def test_get_by_id_returns_log(
        self, client, staff_auth_headers, sample_search_execution_log
    ):
        """
        Given: A log exists with known id
        When: GET /search-execution-logs/{id}
        Then: Returns 200 with that log in JSON:API format
        """
        log_id = sample_search_execution_log.id

        response = client.get(
            f"/search-execution-logs/{log_id}",
            headers=staff_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["type"] == RESPONSE_TYPE
        assert data["data"]["id"] == str(log_id)
        assert data["data"]["attributes"]["status"] == "success"

    def test_get_by_nonexistent_id_returns_404(self, client, staff_auth_headers):
        """
        Given: No log with id=99999
        When: GET /search-execution-logs/99999
        Then: Returns 404
        """
        response = client.get(
            "/search-execution-logs/99999",
            headers=staff_auth_headers,
        )

        assert response.status_code == 404

    def test_get_by_id_without_auth_returns_401_or_403(self, client):
        """
        Given: No authentication token
        When: GET /search-execution-logs/1
        Then: Returns 401 or 403
        """
        response = client.get("/search-execution-logs/1")
        assert response.status_code in (401, 403)
