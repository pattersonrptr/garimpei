"""KeywordSearches over the saved searches module."""

from src.app.alerts.entities import KeywordSearch
from src.app.alerts.ports import KeywordSearches
from src.app.searches.entities import SavedSearch
from src.app.searches.use_cases import (
    CreateSavedSearchUseCase,
    FindSavedSearchByTermUseCase,
    GetSavedSearchUseCase,
    SavedSearchChanges,
    SavedSearchNotFoundError,
    UpdateSavedSearchUseCase,
)


def _to_keyword_search(config: SavedSearch) -> KeywordSearch:
    return KeywordSearch(
        id=config.id,
        search_term=config.search_term,
        is_active=config.is_active,
        frequency_days=config.frequency_days,
        user_id=config.user_id,
        source_website_ids=list(config.source_website_ids),
    )


class SearchConfigKeywordSearches(KeywordSearches):
    def __init__(
        self,
        create: CreateSavedSearchUseCase,
        get: GetSavedSearchUseCase,
        find_by_term: FindSavedSearchByTermUseCase,
        update: UpdateSavedSearchUseCase,
    ):
        self.create_search = create
        self.get_search = get
        self.find_by_term = find_by_term
        self.update_search = update

    def get_by_search_term_and_user_id(
        self, search_term: str, user_id: int
    ) -> KeywordSearch | None:
        config = self.find_by_term.execute(search_term, user_id)
        return _to_keyword_search(config) if config else None

    def get_by_id(self, search_config_id: int) -> KeywordSearch | None:
        try:
            config = self.get_search.execute(search_config_id)
        except SavedSearchNotFoundError:
            return None
        return _to_keyword_search(config)

    def create(self, search: KeywordSearch) -> KeywordSearch:
        created = self.create_search.execute(
            SavedSearch(
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
        # Only the fields alerts knows change; the others (preferred time,
        # metadata) stay as they are.
        changes = SavedSearchChanges(
            search_term=search.search_term,
            is_active=search.is_active,
            frequency_days=search.frequency_days,
            source_website_ids=list(search.source_website_ids),
        )
        try:
            updated = self.update_search.execute(search_config_id, changes)
        except SavedSearchNotFoundError:
            return None
        return _to_keyword_search(updated)
