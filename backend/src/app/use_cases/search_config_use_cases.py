from src.app.entities.search_config import SearchConfig as SearchConfigEntity
from src.app.interfaces.repositories.price_alert_repository import (
    PriceAlertRepositoryInterface,
)
from src.app.interfaces.repositories.search_config_repository import (
    SearchConfigRepositoryInterface,
)


class CreateSearchConfigUseCase:
    """Create a new search configuration for a user."""

    def __init__(self, search_config_repo: SearchConfigRepositoryInterface):
        self.search_config_repo = search_config_repo

    def execute(self, search_config: SearchConfigEntity) -> SearchConfigEntity:
        return self.search_config_repo.create(search_config)


class GetSearchConfigByIdUseCase:
    """Retrieve a single search config by its id."""

    def __init__(self, search_config_repo: SearchConfigRepositoryInterface):
        self.search_config_repo = search_config_repo

    def execute(self, search_config_id: int) -> SearchConfigEntity | None:
        return self.search_config_repo.get_by_id(search_config_id)


class GetSearchConfigsByUserIdUseCase:
    """Retrieve all search configs for a given user."""

    def __init__(self, search_config_repo: SearchConfigRepositoryInterface):
        self.search_config_repo = search_config_repo

    def execute(self, user_id: int) -> list[SearchConfigEntity]:
        return self.search_config_repo.get_by_user_id(user_id)


class ListSearchConfigsUseCase:
    """List all search configs with pagination and sorting."""

    def __init__(self, search_config_repo: SearchConfigRepositoryInterface):
        self.search_config_repo = search_config_repo

    def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
        user_id: int | None = None,
        search_term: str | None = None,
    ) -> tuple[list[SearchConfigEntity], int]:
        return self.search_config_repo.get_all(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            user_id=user_id,
            search_term=search_term,
        )


class UpdateSearchConfigUseCase:
    """Update an existing search config."""

    def __init__(self, search_config_repo: SearchConfigRepositoryInterface):
        self.search_config_repo = search_config_repo

    def execute(
        self, search_config_id: int, search_config: SearchConfigEntity
    ) -> SearchConfigEntity | None:
        return self.search_config_repo.update(search_config_id, search_config)


class SearchConfigInUseError(Exception):
    """The search still backs price alerts, so deleting it would break them."""

    def __init__(self, alert_count: int):
        super().__init__(f"Search config is used by {alert_count} price alert(s)")
        self.alert_count = alert_count


class DeleteSearchConfigUseCase:
    """Delete a search config by id, unless a price alert still uses it."""

    def __init__(
        self,
        search_config_repo: SearchConfigRepositoryInterface,
        price_alert_repo: PriceAlertRepositoryInterface | None = None,
    ):
        self.search_config_repo = search_config_repo
        self.price_alert_repo = price_alert_repo

    def execute(self, search_config_id: int) -> bool:
        """True if deleted, False if not found; raises SearchConfigInUseError."""
        if self.price_alert_repo is not None:
            in_use = self.price_alert_repo.count_by_search_config_id(search_config_id)
            if in_use:
                raise SearchConfigInUseError(in_use)
        return self.search_config_repo.delete(search_config_id)
