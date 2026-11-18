"""StoreReader over the older source-website repository."""

from src.app.alerts.entities import Store
from src.app.alerts.ports import StoreReader
from src.app.stores.ports import StoreRepositoryInterface


class SourceWebsiteStores(StoreReader):
    def __init__(self, source_websites: StoreRepositoryInterface):
        self.source_websites = source_websites

    def get_by_id(self, source_website_id: int) -> Store | None:
        site = self.source_websites.get_by_id(source_website_id)
        if site is None or site.id is None:
            return None
        return Store(id=site.id, name=site.name)
