"""Stores' use cases.

They take and return plain data (entities, ids, a StoreChanges); a missing
store is a StoreNotFoundError, which the HTTP layer maps to a 404.
"""

from dataclasses import dataclass, replace

from src.app.stores.entities import Store
from src.app.stores.ports import (
    StoreHasOffersError,  # noqa: F401
    StoreRepositoryInterface,
)


class StoreNotFoundError(Exception):
    """No store has this id or name."""


@dataclass(frozen=True)
class StoreChanges:
    """Fields to change on a store; None keeps the current value."""

    name: str | None = None
    base_url: str | None = None
    is_active: bool | None = None


class CreateStoreUseCase:
    def __init__(self, stores: StoreRepositoryInterface):
        self.stores = stores

    def execute(self, store: Store) -> Store:
        return self.stores.create(store)


class GetStoreUseCase:
    def __init__(self, stores: StoreRepositoryInterface):
        self.stores = stores

    def execute(self, store_id: int) -> Store:
        store = self.stores.get_by_id(store_id)
        if store is None:
            raise StoreNotFoundError(store_id)
        return store


class GetStoreByNameUseCase:
    def __init__(self, stores: StoreRepositoryInterface):
        self.stores = stores

    def execute(self, name: str) -> Store:
        store = self.stores.get_by_name(name)
        if store is None:
            raise StoreNotFoundError(name)
        return store


class ListStoresUseCase:
    def __init__(self, stores: StoreRepositoryInterface):
        self.stores = stores

    def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[Store], int]:
        """A page of stores and the total count."""
        return self.stores.get_all(
            limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
        )


class UpdateStoreUseCase:
    def __init__(self, stores: StoreRepositoryInterface):
        self.stores = stores

    def execute(self, store_id: int, changes: StoreChanges) -> Store:
        existing = GetStoreUseCase(self.stores).execute(store_id)
        merged = replace(
            existing,
            name=existing.name if changes.name is None else changes.name,
            base_url=existing.base_url
            if changes.base_url is None
            else changes.base_url,
            is_active=existing.is_active
            if changes.is_active is None
            else changes.is_active,
        )
        updated = self.stores.update(store_id, merged)
        if updated is None:
            raise StoreNotFoundError(store_id)
        return updated


class DeleteStoreUseCase:
    def __init__(self, stores: StoreRepositoryInterface):
        self.stores = stores

    def execute(self, store_id: int) -> None:
        if not self.stores.delete(store_id):
            raise StoreNotFoundError(store_id)
