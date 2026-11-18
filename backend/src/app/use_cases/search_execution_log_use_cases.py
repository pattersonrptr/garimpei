from datetime import UTC, datetime

from src.app.searches.entities import FINISHED_STATUSES, SearchRun, is_stale_run
from src.app.searches.ports import SearchRunRepositoryInterface


class CreateSearchExecutionLogUseCase:
    """Record a new search execution log."""

    def __init__(self, search_execution_log_repo: SearchRunRepositoryInterface):
        self.search_execution_log_repo = search_execution_log_repo

    def execute(self, search_execution_log: SearchRun) -> SearchRun:
        return self.search_execution_log_repo.create(search_execution_log)


class GetSearchExecutionLogByIdUseCase:
    """Retrieve a single search execution log by its id."""

    def __init__(self, search_execution_log_repo: SearchRunRepositoryInterface):
        self.search_execution_log_repo = search_execution_log_repo

    def execute(self, search_execution_log_id: int) -> SearchRun | None:
        return self.search_execution_log_repo.get_by_id(search_execution_log_id)


class GetSearchExecutionLogsBySearchConfigIdUseCase:
    """Retrieve all search execution logs for a given search config."""

    def __init__(self, search_execution_log_repo: SearchRunRepositoryInterface):
        self.search_execution_log_repo = search_execution_log_repo

    def execute(self, search_config_id: int) -> list[SearchRun]:
        return self.search_execution_log_repo.get_by_search_config_id(search_config_id)


class ListSearchExecutionLogsUseCase:
    """List all search execution logs with pagination and sorting."""

    def __init__(self, search_execution_log_repo: SearchRunRepositoryInterface):
        self.search_execution_log_repo = search_execution_log_repo

    def execute(
        self,
        limit: int = 10,
        offset: int = 0,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> tuple[list[SearchRun], int]:
        return self.search_execution_log_repo.get_all(
            limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
        )


class DeleteSearchExecutionLogUseCase:
    """Delete a search execution log by id."""

    def __init__(self, search_execution_log_repo: SearchRunRepositoryInterface):
        self.search_execution_log_repo = search_execution_log_repo

    def execute(self, search_execution_log_id: int) -> bool:
        return self.search_execution_log_repo.delete(search_execution_log_id)


class UpdateSearchExecutionLogUseCase:
    """Record the progress or the outcome of a search run.

    Closing a run (status success or failed) stamps ``finished_at``.
    """

    def __init__(self, search_execution_log_repo: SearchRunRepositoryInterface):
        self.search_execution_log_repo = search_execution_log_repo

    def execute(self, search_execution_log_id: int, changes: dict) -> SearchRun | None:
        changes = {k: v for k, v in changes.items() if v is not None}
        if changes.get("status") in FINISHED_STATUSES:
            changes.setdefault("finished_at", datetime.now(UTC))
        return self.search_execution_log_repo.update(search_execution_log_id, changes)


class GetLatestSearchRunUseCase:
    """The latest run of a search config, closing it first if it was lost."""

    def __init__(self, search_execution_log_repo: SearchRunRepositoryInterface):
        self.search_execution_log_repo = search_execution_log_repo

    def execute(
        self, search_config_id: int, now: datetime | None = None
    ) -> SearchRun | None:
        now = now or datetime.now(UTC)
        latest = self.search_execution_log_repo.get_latest_by_search_config_id(
            search_config_id
        )
        if latest and latest.id and is_stale_run(latest.status, latest.started_at, now):
            latest = self.search_execution_log_repo.update(
                latest.id,
                {
                    "status": "failed",
                    "finished_at": now,
                    "error_message": "The search stopped responding and was closed.",
                },
            )
        return latest
