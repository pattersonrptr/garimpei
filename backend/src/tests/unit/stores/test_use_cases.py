"""Stores' use cases, with an in-memory fake for the repository port.

Only the use cases that decide something are tested here; creating and
listing stores pass straight to the repository and stay covered by the
e2e and characterization tests.
"""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from src.app.stores.entities import Store
from src.app.stores.ports import StoreRepositoryInterface
from src.app.stores.use_cases import (
    DeleteStoreUseCase,
    GetStoreByNameUseCase,
    GetStoreUseCase,
    StoreChanges,
    StoreNotFoundError,
    UpdateStoreUseCase,
)

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
SEBO = Store(
    id=1,
    name="Sebo",
    base_url="https://sebo.example.com",
    is_active=False,
    created_at=CREATED,
    updated_at=CREATED,
)


class FakeStores(StoreRepositoryInterface):
    def __init__(self, *stores: Store):
        self.rows = {s.id: s for s in stores}

    def create(self, source_website: Store) -> Store:
        created = replace(source_website, id=max(self.rows, default=0) + 1)
        self.rows[created.id] = created
        return created

    def get_by_id(self, source_website_id: int) -> Store | None:
        return self.rows.get(source_website_id)

    def get_by_name(self, name: str) -> Store | None:
        return next((s for s in self.rows.values() if s.name == name), None)

    def get_all(self, limit=10, offset=0, sort_by=None, sort_order=None):
        stores = list(self.rows.values())
        return stores[offset : offset + limit], len(stores)

    def update(self, source_website_id: int, source_website: Store) -> Store | None:
        if source_website_id not in self.rows:
            return None
        self.rows[source_website_id] = source_website
        return source_website

    def delete(self, source_website_id: int) -> bool:
        return self.rows.pop(source_website_id, None) is not None


class TestGetStore:
    def test_a_store_is_found_by_id(self):
        assert GetStoreUseCase(FakeStores(SEBO)).execute(1) == SEBO

    def test_a_missing_store_is_not_found(self):
        with pytest.raises(StoreNotFoundError):
            GetStoreUseCase(FakeStores(SEBO)).execute(99)

    def test_a_store_is_found_by_name(self):
        assert GetStoreByNameUseCase(FakeStores(SEBO)).execute("Sebo") == SEBO

    def test_a_missing_name_is_not_found(self):
        with pytest.raises(StoreNotFoundError):
            GetStoreByNameUseCase(FakeStores(SEBO)).execute("OLX")


class TestUpdateStore:
    def test_an_update_changes_only_the_fields_given(self):
        stores = FakeStores(SEBO)

        updated = UpdateStoreUseCase(stores).execute(1, StoreChanges(name="Sebo Novo"))

        assert (updated.name, updated.base_url, updated.is_active) == (
            "Sebo Novo",
            "https://sebo.example.com",
            False,
        )
        assert stores.get_by_id(1) == updated

    def test_an_update_can_turn_a_flag_off(self):
        active = replace(SEBO, is_active=True)
        stores = FakeStores(active)

        updated = UpdateStoreUseCase(stores).execute(1, StoreChanges(is_active=False))

        assert updated.is_active is False
        assert updated.name == "Sebo"

    def test_updating_a_missing_store_is_not_found(self):
        with pytest.raises(StoreNotFoundError):
            UpdateStoreUseCase(FakeStores(SEBO)).execute(99, StoreChanges(name="X"))


class TestDeleteStore:
    def test_a_deleted_store_is_gone(self):
        stores = FakeStores(SEBO)

        DeleteStoreUseCase(stores).execute(1)

        assert stores.get_by_id(1) is None

    def test_deleting_a_missing_store_is_not_found(self):
        with pytest.raises(StoreNotFoundError):
            DeleteStoreUseCase(FakeStores(SEBO)).execute(99)
