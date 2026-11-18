"""StoreDirectory over the stores module's use cases."""

from src.app.catalog.ports import StoreDirectory
from src.app.stores.use_cases import (
    GetStoreByNameUseCase,
    GetStoreUseCase,
    StoreNotFoundError,
)


class StoreDirectoryOverStores(StoreDirectory):
    def __init__(self, by_id: GetStoreUseCase, by_name: GetStoreByNameUseCase):
        self.by_id = by_id
        self.by_name = by_name

    def exists(self, store_id: int) -> bool:
        try:
            self.by_id.execute(store_id)
        except StoreNotFoundError:
            return False
        return True

    def id_named(self, name: str) -> int | None:
        try:
            return self.by_name.execute(name).id
        except StoreNotFoundError:
            return None
