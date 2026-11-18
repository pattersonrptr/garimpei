"""StoreReader over the stores module."""

from src.app.alerts.entities import Store
from src.app.alerts.ports import StoreReader
from src.app.stores.use_cases import GetStoreUseCase, StoreNotFoundError


class StoreReaderOverStores(StoreReader):
    def __init__(self, store_by_id: GetStoreUseCase):
        self.store_by_id = store_by_id

    def get_by_id(self, source_website_id: int) -> Store | None:
        try:
            store = self.store_by_id.execute(source_website_id)
        except StoreNotFoundError:
            return None
        if store.id is None:
            return None
        return Store(id=store.id, name=store.name)
