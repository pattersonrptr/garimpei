"""KeywordSearches over the older SearchConfig repository."""

from src.app.alerts.entities import KeywordSearch
from src.app.alerts.ports import KeywordSearches
from src.app.entities.search_config import SearchConfig
from src.app.interfaces.repositories.search_config_repository import (
    SearchConfigRepositoryInterface,
)


def _to_keyword_search(config: SearchConfig) -> KeywordSearch:
    return KeywordSearch(
        id=config.id,
        search_term=config.search_term,
        is_active=config.is_active,
        frequency_days=config.frequency_days,
        user_id=config.user_id,
        source_website_ids=list(config.source_website_ids),
    )


class SearchConfigKeywordSearches(KeywordSearches):
    def __init__(self, search_configs: SearchConfigRepositoryInterface):
        self.search_configs = search_configs

    def get_by_search_term_and_user_id(
        self, search_term: str, user_id: int
    ) -> KeywordSearch | None:
        config = self.search_configs.get_by_search_term_and_user_id(
            search_term, user_id
        )
        return _to_keyword_search(config) if config else None

    def get_by_id(self, search_config_id: int) -> KeywordSearch | None:
        config = self.search_configs.get_by_id(search_config_id)
        return _to_keyword_search(config) if config else None

    def create(self, search: KeywordSearch) -> KeywordSearch:
        created = self.search_configs.create(
            SearchConfig(
                search_term=search.search_term,
                is_active=search.is_active,
                frequency_days=search.frequency_days,
                user_id=search.user_id,
                source_website_ids=list(search.source_website_ids),
            )
        )
        return _to_keyword_search(created)

    def update(
        self, search_config_id: int, search: KeywordSearch
    ) -> KeywordSearch | None:
        # Read first so the fields alerts does not know (preferred time,
        # metadata) are saved back unchanged.
        config = self.search_configs.get_by_id(search_config_id)
        if config is None:
            return None
        config.search_term = search.search_term
        config.is_active = search.is_active
        config.frequency_days = search.frequency_days
        config.user_id = search.user_id
        config.source_website_ids = list(search.source_website_ids)
        updated = self.search_configs.update(search_config_id, config)
        return _to_keyword_search(updated) if updated else None
