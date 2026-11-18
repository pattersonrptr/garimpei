"""Characterization tests before the stores module (source websites).

They pin today's behavior over HTTP, so the refactor that moves source
websites into their own module can prove it changed nothing. Each test
kills a mutation that survived the existing suite (Nov 18, 2026).
"""

from datetime import datetime

from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.stores.persistence.models import Store as StoreModel

OLD = datetime(2026, 1, 1, 12, 0, 0)


def add_store(test_db, name, created_at=None, **fields):
    store = StoreModel(
        name=name,
        base_url=fields.pop("base_url", f"https://{name.lower()}.example.com"),
        is_active=fields.pop("is_active", True),
        **({"created_at": created_at} if created_at else {}),
        **fields,
    )
    test_db.add(store)
    test_db.commit()
    test_db.refresh(store)
    return store


def update(client, headers, store_id, **attributes):
    return client.put(
        f"/source-websites/{store_id}",
        json={"data": {"type": "source_website", "attributes": attributes}},
        headers=headers,
    )


def listed_names(client, headers, **params):
    response = client.get("/source-websites/", params=params, headers=headers)
    assert response.status_code == 200
    return [item["attributes"]["name"] for item in response.json()["data"]]


def attributes_of(client, headers, store_id):
    response = client.get(f"/source-websites/{store_id}", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]["attributes"]


class TestOnlyStaffChangesStores:
    def test_a_regular_user_cannot_create_a_store(self, client, auth_headers):
        response = client.post(
            "/source-websites/",
            json={
                "data": {
                    "type": "source_website",
                    "attributes": {"name": "OLX", "base_url": "https://olx.com.br"},
                }
            },
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert (
            client.get("/source-websites/name/OLX", headers=auth_headers).status_code
            == 404
        )

    def test_a_regular_user_cannot_update_a_store(
        self, client, auth_headers, sample_source_website
    ):
        response = update(
            client, auth_headers, sample_source_website.id, name="Renamed"
        )

        assert response.status_code == 403
        assert (
            attributes_of(client, auth_headers, sample_source_website.id)["name"]
            == "Test Website"
        )

    def test_a_regular_user_cannot_delete_a_store(
        self, client, auth_headers, sample_source_website
    ):
        response = client.delete(
            f"/source-websites/{sample_source_website.id}", headers=auth_headers
        )

        assert response.status_code == 403
        attributes_of(client, auth_headers, sample_source_website.id)


class TestPartialUpdate:
    def test_fields_left_out_of_an_update_keep_their_values(
        self, client, test_db, staff_auth_headers
    ):
        store = add_store(
            test_db, "Sebo", base_url="https://sebo.example.com", is_active=False
        )

        response = update(client, staff_auth_headers, store.id, name="Sebo Novo")

        assert response.status_code == 200
        attributes = attributes_of(client, staff_auth_headers, store.id)
        assert attributes["name"] == "Sebo Novo"
        assert attributes["base_url"] == "https://sebo.example.com"
        assert attributes["is_active"] is False

    def test_an_update_of_only_the_url_keeps_the_name(
        self, client, test_db, staff_auth_headers
    ):
        store = add_store(test_db, "Sebo")

        update(
            client, staff_auth_headers, store.id, base_url="https://novo.example.com"
        )

        attributes = attributes_of(client, staff_auth_headers, store.id)
        assert attributes["name"] == "Sebo"
        assert attributes["base_url"] == "https://novo.example.com"

    def test_an_update_moves_updated_at_forward(
        self, client, test_db, staff_auth_headers
    ):
        store = add_store(test_db, "Sebo", updated_at=OLD)

        update(client, staff_auth_headers, store.id, is_active=False)

        updated_at = attributes_of(client, staff_auth_headers, store.id)["updated_at"]
        assert datetime.fromisoformat(updated_at).replace(tzinfo=None) > OLD


class TestListOrder:
    def test_without_sort_the_newest_store_comes_first(
        self, client, test_db, auth_headers
    ):
        add_store(test_db, "Old", created_at=datetime(2026, 1, 1))
        add_store(test_db, "New", created_at=datetime(2026, 6, 1))
        add_store(test_db, "Middle", created_at=datetime(2026, 3, 1))

        assert listed_names(client, auth_headers) == ["New", "Middle", "Old"]

    def test_sorting_by_a_field_is_descending_unless_asked_otherwise(
        self, client, test_db, auth_headers
    ):
        for name in ("Bravo", "Alpha", "Charlie"):
            add_store(test_db, name)

        assert listed_names(client, auth_headers, sort_by="name") == [
            "Charlie",
            "Bravo",
            "Alpha",
        ]
        assert listed_names(client, auth_headers, sort_by="name", sort_order="asc") == [
            "Alpha",
            "Bravo",
            "Charlie",
        ]

    def test_sorting_by_an_unknown_field_falls_back_to_newest_first(
        self, client, test_db, auth_headers
    ):
        add_store(test_db, "Old", created_at=datetime(2026, 1, 1))
        add_store(test_db, "New", created_at=datetime(2026, 6, 1))

        assert listed_names(client, auth_headers, sort_by="no_such_field") == [
            "New",
            "Old",
        ]


class TestDeleteStoreInUse:
    def test_deleting_a_store_an_alert_uses_removes_it_from_the_alert(
        self, client, test_db, staff_auth_headers, sample_user, sample_source_website
    ):
        alert = PriceAlertModel(
            search_term="dom casmurro",
            max_price=30.0,
            is_active=True,
            user_id=sample_user.id,
        )
        alert.source_websites.append(sample_source_website)
        test_db.add(alert)
        test_db.commit()

        response = client.delete(
            f"/source-websites/{sample_source_website.id}", headers=staff_auth_headers
        )

        assert response.status_code == 204
        test_db.expire_all()
        assert test_db.get(PriceAlertModel, alert.id).source_websites == []

    def test_deleting_a_store_a_saved_search_uses_removes_it_from_the_search(
        self,
        client,
        test_db,
        staff_auth_headers,
        sample_search_config,
        sample_source_website,
    ):
        sample_search_config.source_websites.append(sample_source_website)
        test_db.commit()

        response = client.delete(
            f"/source-websites/{sample_source_website.id}", headers=staff_auth_headers
        )

        assert response.status_code == 204
        test_db.expire_all()
        assert (
            test_db.get(
                type(sample_search_config), sample_search_config.id
            ).source_websites
            == []
        )
