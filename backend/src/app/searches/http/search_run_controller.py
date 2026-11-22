from typing import cast

from fastapi import APIRouter, Depends, Query, status

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import get_current_staff_user
from src.app.infrastructure.database_config import get_db
from src.app.searches import wiring
from src.app.searches.entities import SearchRun, SearchRunStatus
from src.app.searches.http.search_run_presenter import (
    SearchRunPresenter,
)
from src.app.searches.http.search_run_schema import (
    SearchRunCreateRequest,
    SearchRunReadResponse,
    SearchRunsCollectionResponse,
    SearchRunUpdateRequest,
)
from src.app.searches.ports import SearchRunRepositoryInterface
from src.app.searches.use_cases import (
    CreateSearchRunUseCase,
    GetRunsOfSearchUseCase,
    GetSearchRunUseCase,
    ListSearchRunsUseCase,
    SearchRunChanges,
    SearchRunNotFoundError,
    UpdateSearchRunUseCase,
)
from src.config.logging_config import get_logger

router = APIRouter(tags=["search_execution_logs"], prefix="/search-execution-logs")

logger = get_logger(__name__)


def get_search_execution_log_repository(
    db=Depends(get_db),
) -> SearchRunRepositoryInterface:
    return wiring.search_runs(db)


@router.get("/", response_model=SearchRunsCollectionResponse)
def list_search_execution_logs(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default="desc", pattern="^(asc|desc)$"),
    search_execution_log_repo: SearchRunRepositoryInterface = Depends(
        get_search_execution_log_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    List all search execution logs with pagination. Requires staff or superuser access.

    Returns:
        - 200: Collection of search execution logs with pagination meta
        - 403: Permission denied
    """
    logger.debug(
        f"Listing search execution logs: limit={limit}, offset={offset}",
        extra={"action": "list_search_execution_logs", "user_id": current_user.id},
    )

    use_case = ListSearchRunsUseCase(search_execution_log_repo)
    records, total = use_case.execute(
        limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
    )
    return SearchRunPresenter.handle_collection_success(records, total)


@router.get(
    "/search-config/{search_config_id}",
    response_model=SearchRunsCollectionResponse,
)
def get_search_execution_logs_by_search_config(
    search_config_id: int,
    search_execution_log_repo: SearchRunRepositoryInterface = Depends(
        get_search_execution_log_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Get all search execution logs for a given search config.
    Requires staff or superuser access.

    Returns:
        - 200: Collection of search execution logs
        - 403: Permission denied
    """
    logger.debug(
        f"Getting search execution logs for search_config_id: {search_config_id}",
        extra={
            "action": "get_search_execution_logs_by_search_config",
            "user_id": current_user.id,
        },
    )

    use_case = GetRunsOfSearchUseCase(search_execution_log_repo)
    records = use_case.execute(search_config_id)
    return SearchRunPresenter.handle_collection_success(records, len(records))


@router.get("/{search_execution_log_id}", response_model=SearchRunReadResponse)
def get_search_execution_log(
    search_execution_log_id: int,
    search_execution_log_repo: SearchRunRepositoryInterface = Depends(
        get_search_execution_log_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Get a single search execution log by ID. Requires staff or superuser access.

    Returns:
        - 200: Search execution log found
        - 403: Permission denied
        - 404: Not found
    """
    logger.debug(
        f"Getting search execution log ID: {search_execution_log_id}",
        extra={
            "action": "get_search_execution_log",
            "user_id": current_user.id,
        },
    )

    use_case = GetSearchRunUseCase(search_execution_log_repo)
    try:
        record = use_case.execute(search_execution_log_id)
    except SearchRunNotFoundError:
        return SearchRunPresenter.handle_not_found(
            f"id {search_execution_log_id}", "/data/id"
        )

    return SearchRunPresenter.handle_success(record)


@router.post(
    "/",
    response_model=SearchRunReadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_search_execution_log(
    payload: SearchRunCreateRequest,
    search_execution_log_repo: SearchRunRepositoryInterface = Depends(
        get_search_execution_log_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Create a new search execution log. Requires staff or superuser access.

    Returns:
        - 201: Search execution log created successfully
        - 403: Permission denied
    """
    attrs = payload.data.attributes
    logger.debug(
        f"Creating search execution log for search_config_id={attrs.search_config_id}",
        extra={
            "action": "create_search_execution_log",
            "user_id": current_user.id,
        },
    )

    entity = SearchRun(
        search_config_id=attrs.search_config_id,
        status=cast(SearchRunStatus, attrs.status),
        results_count=attrs.results_count,
        listings_found=attrs.listings_found,
        listings_checked=attrs.listings_checked,
        error_message=attrs.error_message,
    )
    use_case = CreateSearchRunUseCase(search_execution_log_repo)
    created = use_case.execute(entity)
    return SearchRunPresenter.handle_success(created)


@router.patch("/{search_execution_log_id}", response_model=SearchRunReadResponse)
def update_search_execution_log(
    search_execution_log_id: int,
    payload: SearchRunUpdateRequest,
    search_execution_log_repo: SearchRunRepositoryInterface = Depends(
        get_search_execution_log_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Record the progress or the outcome of a search run. Requires staff access
    (the scrapers' service user). Setting status to success or failed closes
    the run and stamps finished_at.

    Returns:
        - 200: Updated log
        - 403: Permission denied
        - 404: Log not found
    """
    attrs = payload.data.attributes
    use_case = UpdateSearchRunUseCase(search_execution_log_repo)
    try:
        updated = use_case.execute(
            search_execution_log_id,
            SearchRunChanges(
                status=attrs.status,
                results_count=attrs.results_count,
                listings_found=attrs.listings_found,
                listings_checked=attrs.listings_checked,
                error_message=attrs.error_message,
            ),
        )
    except SearchRunNotFoundError:
        return SearchRunPresenter.handle_not_found(
            f"id {search_execution_log_id}", "/data/id"
        )
    return SearchRunPresenter.handle_success(updated)
