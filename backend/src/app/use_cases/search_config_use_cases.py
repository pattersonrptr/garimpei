from src.app.entities.search_config import SearchConfig as SearchConfigEntity
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
    ) -> tuple[list[SearchConfigEntity], int]:
        return self.search_config_repo.get_all(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            user_id=user_id,
        )


class UpdateSearchConfigUseCase:
    """Update an existing search config."""

    def __init__(self, search_config_repo: SearchConfigRepositoryInterface):
        self.search_config_repo = search_config_repo

    def execute(
        self, search_config_id: int, search_config: SearchConfigEntity
    ) -> SearchConfigEntity | None:
        return self.search_config_repo.update(search_config_id, search_config)


class DeleteSearchConfigUseCase:
    """Delete a search config by id."""

    def __init__(self, search_config_repo: SearchConfigRepositoryInterface):
        self.search_config_repo = search_config_repo

    def execute(self, search_config_id: int) -> bool:
        return self.search_config_repo.delete(search_config_id)
