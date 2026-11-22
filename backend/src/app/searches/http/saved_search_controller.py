from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import (
    can_access_owned_resource,
    get_current_active_user,
    get_current_staff_user,
    is_staff_or_superuser,
)
from src.app.infrastructure.database_config import get_db
from src.app.searches import wiring
from src.app.searches.entities import RunLimitViolation, SavedSearch
from src.app.searches.http.saved_search_presenter import (
    SavedSearchPresenter,
)
from src.app.searches.http.saved_search_schema import (
    SavedSearchCreateRequest,
    SavedSearchesCollectionResponse,
    SavedSearchReadResponse,
    SavedSearchUpdateRequest,
)
from src.app.searches.http.validators import SavedSearchValidator
from src.app.searches.ports import (
    SavedSearchRepositoryInterface,
    SearchRunRepositoryInterface,
)
from src.app.searches.use_cases import (
    CreateSavedSearchUseCase,
    DeleteSavedSearchUseCase,
    GetLatestSearchRunUseCase,
    GetSavedSearchesOfUserUseCase,
    GetSavedSearchUseCase,
    ListSavedSearchesUseCase,
    RunLimitReachedError,
    RunSearchNowUseCase,
    SavedSearchChanges,
    SavedSearchInUseError,
    SavedSearchNotFoundError,
    SearchAlreadyRunningError,
    UpdateSavedSearchUseCase,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse
from src.config.logging_config import get_logger

router = APIRouter(tags=["search_configs"], prefix="/search-configs")

logger = get_logger(__name__)


def _plan_limit_error(violation: RunLimitViolation) -> JsonApiError:
    """A plan limit a manual run breaks, as a JSON:API error."""
    return JsonApiError(
        status="403",
        code="PLAN_LIMIT_REACHED",
        title=violation.title,
        detail=violation.detail,
        source={"pointer": violation.pointer} if violation.pointer else None,
        meta=violation.meta,
    )


def _owned_search(
    searches: SavedSearchRepositoryInterface, search_id: int, user: UserEntity
) -> SavedSearch | None:
    """The saved search, or None when it is missing or not the user's."""
    try:
        search = GetSavedSearchUseCase(searches).execute(search_id)
    except SavedSearchNotFoundError:
        return None
    return search if can_access_owned_resource(search.user_id, user) else None


def get_search_config_repository(
    db=Depends(get_db),
) -> SavedSearchRepositoryInterface:
    return wiring.saved_searches(db)


def get_search_execution_log_repository(
    db=Depends(get_db),
) -> SearchRunRepositoryInterface:
    return wiring.search_runs(db)


def get_delete_saved_search(db=Depends(get_db)) -> DeleteSavedSearchUseCase:
    return wiring.delete_saved_search(db)


def get_run_search_now(db=Depends(get_db)) -> RunSearchNowUseCase:
    return wiring.run_search_now(db)


def get_search_config_validator(db=Depends(get_db)) -> SavedSearchValidator:
    return wiring.saved_search_validator(db)


@router.post("/", response_model=SavedSearchReadResponse, status_code=201)
def create_search_config(
    search_config_in: SavedSearchCreateRequest,
    search_config_repo: SavedSearchRepositoryInterface = Depends(
        get_search_config_repository
    ),
    search_config_validator: SavedSearchValidator = Depends(
        get_search_config_validator
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Create a new search configuration. Requires staff or superuser access (regular users get search configs through their price alerts).

    Returns:
        - 201: Search config created successfully
        - 400: Validation errors (invalid type)
        - 403: Permission denied
        - 404: Referenced source website not found
        - 409: Duplicate search term for this user
        - 422: Invalid field values
    """
    logger.info(
        f"Creating new search config: '{search_config_in.data.attributes.search_term}'",
        extra={"action": "create_search_config", "user_id": current_user.id},
    )

    validation_errors = search_config_validator.validate_create_request(
        search_config_in
    )
    if validation_errors:
        logger.warning(
            f"Search config creation validation failed: {len(validation_errors)} errors",
            extra={
                "action": "search_config_validation_failed",
                "user_id": current_user.id,
            },
        )
        return SavedSearchPresenter.handle_validation_errors(validation_errors)

    attrs = search_config_in.data.attributes
    search_config_entity = SavedSearch(
        search_term=attrs.search_term,
        is_active=attrs.is_active,
        frequency_days=attrs.frequency_days,
        preferred_time=attrs.preferred_time,
        search_metadata=attrs.search_metadata,
        user_id=attrs.user_id,
        source_website_ids=attrs.source_website_ids,
    )

    use_case = CreateSavedSearchUseCase(search_config_repo)
    created = use_case.execute(search_config_entity)

    logger.info(
        f"Search config created: '{created.search_term}' (ID: {created.id})",
        extra={
            "action": "search_config_created",
            "search_config_id": created.id,
            "user_id": current_user.id,
        },
    )
    return SavedSearchPresenter.handle_success(created)


@router.get("/", response_model=SavedSearchesCollectionResponse)
def list_search_configs(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default="desc", pattern="^(asc|desc)$"),
    search_term: str | None = Query(default=None, max_length=255),
    search_config_repo: SavedSearchRepositoryInterface = Depends(
        get_search_config_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    List all search configs with pagination (newest first). ``search_term``
    keeps the configs whose term contains it, ignoring case and accents. Regular users can only access their own search configs; staff can access all.

    Returns:
        - 200: Collection of search configs with pagination meta
        - 403: Permission denied
    """
    logger.debug(
        f"Listing search configs: limit={limit}, offset={offset}",
        extra={"action": "list_search_configs", "user_id": current_user.id},
    )

    use_case = ListSavedSearchesUseCase(search_config_repo)
    search_configs, total = use_case.execute(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        # Staff (incl. the Celery worker) see every config; users see their own.
        user_id=None if is_staff_or_superuser(current_user) else current_user.id,
        search_term=search_term.strip() if search_term else None,
    )
    return SavedSearchPresenter.handle_collection_success(search_configs, total)


@router.get("/user/{user_id}", response_model=SavedSearchesCollectionResponse)
def get_search_configs_by_user(
    user_id: int,
    search_config_repo: SavedSearchRepositoryInterface = Depends(
        get_search_config_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get all search configs for a specific user. Regular users can only access their own search configs; staff can access all.

    Returns:
        - 200: Collection of search configs for the user
        - 403: Permission denied
    """
    logger.debug(
        f"Getting search configs for user_id: {user_id}",
        extra={
            "action": "get_search_configs_by_user",
            "target_user_id": user_id,
            "user_id": current_user.id,
        },
    )

    use_case = GetSavedSearchesOfUserUseCase(search_config_repo)
    if not can_access_owned_resource(user_id, current_user):
        raise HTTPException(
            status_code=403,
            detail="You can only list your own search configs.",
        )

    search_configs = use_case.execute(user_id)
    return SavedSearchPresenter.handle_collection_success(
        search_configs, len(search_configs)
    )


@router.get("/{search_config_id}", response_model=SavedSearchReadResponse)
def get_search_config(
    search_config_id: int,
    search_config_repo: SavedSearchRepositoryInterface = Depends(
        get_search_config_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get a single search config by ID. Regular users can only access their own search configs; staff can access all.

    Returns:
        - 200: Search config found
        - 403: Permission denied
        - 404: Search config not found
    """
    logger.debug(
        f"Getting search config ID: {search_config_id}",
        extra={
            "action": "get_search_config",
            "search_config_id": search_config_id,
            "user_id": current_user.id,
        },
    )

    search_config = _owned_search(search_config_repo, search_config_id, current_user)
    if search_config is None:
        return SavedSearchPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    return SavedSearchPresenter.handle_success(search_config)


@router.put("/{search_config_id}", response_model=SavedSearchReadResponse)
def update_search_config(
    search_config_id: int,
    search_config_in: SavedSearchUpdateRequest,
    search_config_repo: SavedSearchRepositoryInterface = Depends(
        get_search_config_repository
    ),
    search_config_validator: SavedSearchValidator = Depends(
        get_search_config_validator
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Update an existing search config. Requires staff or superuser access (regular users get search configs through their price alerts).

    Returns:
        - 200: Search config updated successfully
        - 400: Validation errors (invalid type)
        - 403: Permission denied
        - 404: Search config not found
        - 409: Duplicate search term for same user
        - 422: Invalid field values
    """
    logger.info(
        f"Updating search config ID: {search_config_id}",
        extra={
            "action": "update_search_config",
            "search_config_id": search_config_id,
            "user_id": current_user.id,
        },
    )

    if _owned_search(search_config_repo, search_config_id, current_user) is None:
        return SavedSearchPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    validation_errors = search_config_validator.validate_update_request(
        search_config_id, search_config_in
    )
    if validation_errors:
        logger.warning(
            f"Search config update validation failed: {len(validation_errors)} errors",
            extra={
                "action": "search_config_update_validation_failed",
                "search_config_id": search_config_id,
            },
        )
        return SavedSearchPresenter.handle_validation_errors(validation_errors)

    attrs = search_config_in.data.attributes
    updated = UpdateSavedSearchUseCase(search_config_repo).execute(
        search_config_id,
        SavedSearchChanges(
            search_term=attrs.search_term,
            is_active=attrs.is_active,
            frequency_days=attrs.frequency_days,
            preferred_time=attrs.preferred_time,
            search_metadata=attrs.search_metadata,
            source_website_ids=attrs.source_website_ids,
        ),
    )

    logger.info(
        f"Search config updated: '{updated.search_term}' (ID: {search_config_id})",
        extra={
            "action": "search_config_updated",
            "search_config_id": search_config_id,
            "user_id": current_user.id,
        },
    )
    return SavedSearchPresenter.handle_success(updated)


@router.delete("/{search_config_id}", status_code=204)
def delete_search_config(
    search_config_id: int,
    search_config_repo: SavedSearchRepositoryInterface = Depends(
        get_search_config_repository
    ),
    delete_saved_search: DeleteSavedSearchUseCase = Depends(get_delete_saved_search),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Delete a search config. Requires staff or superuser access (regular users get search configs through their price alerts).

    Returns:
        - 204: Deleted successfully (no content)
        - 403: Permission denied
        - 404: Search config not found
        - 409: Price alerts still use this search
    """
    logger.warning(
        f"Deleting search config ID: {search_config_id}",
        extra={
            "action": "delete_search_config",
            "search_config_id": search_config_id,
            "user_id": current_user.id,
        },
    )

    search_config = _owned_search(search_config_repo, search_config_id, current_user)
    if search_config is None:
        return SavedSearchPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    try:
        delete_saved_search.execute(search_config_id)
    except SavedSearchInUseError as in_use:
        return JSONResponse(
            status_code=409,
            content=JsonApiErrorResponse(
                errors=[
                    JsonApiError(
                        status="409",
                        code="SEARCH_CONFIG_IN_USE",
                        title="Search in use",
                        detail=(
                            f"This search is used by {in_use.alert_count} price "
                            "alert(s). Delete or change those alerts first."
                        ),
                        meta={"alert_count": in_use.alert_count},
                    )
                ]
            ).model_dump(),
            media_type="application/vnd.api+json",
        )
    except SavedSearchNotFoundError:
        return SavedSearchPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    logger.warning(
        f"Search config deleted (ID: {search_config_id})",
        extra={
            "action": "search_config_deleted",
            "search_config_id": search_config_id,
            "user_id": current_user.id,
        },
    )
    return None


# ---------------------------------------------------------------------------
# Trigger & execution status
# ---------------------------------------------------------------------------


@router.post("/{search_config_id}/trigger", status_code=202)
def trigger_search_config(
    search_config_id: int,
    search_config_repo: SavedSearchRepositoryInterface = Depends(
        get_search_config_repository
    ),
    run_now: RunSearchNowUseCase = Depends(get_run_search_now),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Manually trigger a scraper search for a search config ("Run Now").

    Regular users can only trigger searches that back one of their own
    active price alerts, within their plan: the alert's sources must fit the
    plan and a manual run can't happen sooner than the plan's minimum check
    interval since the last run. Staff are not limited.

    Dispatches a Celery task if the config is not already running.

    Returns:
        - 202: Task dispatched
        - 403: Plan limit reached (sources or minimum interval)
        - 404: Search config not found (or not linked to your active alerts)
        - 409: Already running
    """
    search_config = _owned_search(search_config_repo, search_config_id, current_user)
    if search_config is None:
        return SavedSearchPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    try:
        task_id = run_now.execute(
            search_config,
            user_id=current_user.id,
            user_is_staff=is_staff_or_superuser(current_user),
        )
    except SavedSearchNotFoundError:  # not behind one of the user's alerts
        return SavedSearchPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )
    except RunLimitReachedError as refused:
        return JSONResponse(
            status_code=403,
            content=JsonApiErrorResponse(
                errors=[_plan_limit_error(refused.violation)]
            ).model_dump(),
            media_type="application/vnd.api+json",
        )
    except SearchAlreadyRunningError:
        logger.info(
            "Search config %s already running, skipping trigger",
            search_config_id,
            extra={
                "action": "trigger_search_config_skipped",
                "search_config_id": search_config_id,
            },
        )
        return JSONResponse(
            status_code=409,
            content={
                "data": {
                    "type": "search_config_trigger",
                    "attributes": {
                        "status": "already_running",
                        "search_config_id": search_config_id,
                        "message": "Search is already running for this config.",
                    },
                }
            },
        )

    logger.info(
        "Triggered scraper search for config %s (task %s)",
        search_config_id,
        task_id,
        extra={
            "action": "trigger_search_config",
            "search_config_id": search_config_id,
            "task_id": task_id,
            "user_id": current_user.id,
        },
    )
    return JSONResponse(
        status_code=202,
        content={
            "data": {
                "type": "search_config_trigger",
                "attributes": {
                    "status": "dispatched",
                    "search_config_id": search_config_id,
                    "task_id": task_id,
                },
            }
        },
    )


@router.get("/{search_config_id}/execution-status")
def get_execution_status(
    search_config_id: int,
    search_config_repo: SavedSearchRepositoryInterface = Depends(
        get_search_config_repository
    ),
    log_repo: SearchRunRepositoryInterface = Depends(
        get_search_execution_log_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get the latest execution status for a search config.

    Returns:
        - 200: Latest execution status (idle / pending / running / success / failed)
        - 404: Search config not found
    """
    search_config = _owned_search(search_config_repo, search_config_id, current_user)
    if search_config is None:
        return SavedSearchPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    latest_log = GetLatestSearchRunUseCase(log_repo).execute(search_config_id)

    if not latest_log:
        return {
            "data": {
                "type": "execution_status",
                "attributes": {
                    "search_config_id": search_config_id,
                    "status": "idle",
                    "started_at": None,
                    "finished_at": None,
                    "results_count": None,
                    "listings_found": None,
                    "listings_checked": None,
                    "error_message": None,
                },
            }
        }

    return {
        "data": {
            "type": "execution_status",
            "attributes": {
                "search_config_id": search_config_id,
                "status": latest_log.status,
                "started_at": latest_log.started_at.isoformat()
                if latest_log.started_at
                else None,
                "finished_at": latest_log.finished_at.isoformat()
                if latest_log.finished_at
                else None,
                "results_count": latest_log.results_count,
                "listings_found": latest_log.listings_found,
                "listings_checked": latest_log.listings_checked,
                "error_message": latest_log.error_message,
            },
        }
    }
