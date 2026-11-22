"""SearchStores over the stores module."""

from src.app.searches.ports import SearchStores
from src.app.stores.use_cases import GetStoreUseCase, StoreNotFoundError


class SearchStoresOverStores(SearchStores):
    def __init__(self, store_by_id: GetStoreUseCase):
        self.store_by_id = store_by_id

    def exists(self, store_id: int) -> bool:
        try:
            self.store_by_id.execute(store_id)
        except StoreNotFoundError:
            return False
        return True
