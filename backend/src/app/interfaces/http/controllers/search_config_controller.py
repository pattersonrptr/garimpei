from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from src.app.domain.plan_limits import (
    PlanLimits,
    manual_run_violation,
    source_limit_violation,
)
from src.app.domain.validators.search_config_validator import SearchConfigValidator
from src.app.entities.search_config import SearchConfig as SearchConfigEntity
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.celery_client import dispatch_scraper_search
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.price_alert_repository import (
    PriceAlertRepository,
)
from src.app.infrastructure.repositories.search_config_repository import (
    SearchConfigRepository,
)
from src.app.infrastructure.repositories.search_execution_log_repository import (
    SearchExecutionLogRepository,
)
from src.app.infrastructure.repositories.source_website_repository import (
    SourceWebsiteRepository,
)
from src.app.interfaces.http.plan_limits import get_user_plan_limits, to_jsonapi_error
from src.app.interfaces.http.presenters.search_config_presenter import (
    SearchConfigPresenter,
)
from src.app.interfaces.http.schemas.search_config_schema import (
    SearchConfigCreateRequest,
    SearchConfigReadResponse,
    SearchConfigsCollectionResponse,
    SearchConfigUpdateRequest,
)
from src.app.security.auth import (
    can_access_owned_resource,
    get_current_active_user,
    get_current_staff_user,
    is_staff_or_superuser,
)
from src.app.use_cases.search_config_use_cases import (
    CreateSearchConfigUseCase,
    DeleteSearchConfigUseCase,
    GetSearchConfigByIdUseCase,
    GetSearchConfigsByUserIdUseCase,
    ListSearchConfigsUseCase,
    UpdateSearchConfigUseCase,
)
from src.common.jsonapi import JsonApiErrorResponse
from src.config.logging_config import get_logger

router = APIRouter(tags=["search_configs"], prefix="/search-configs")

logger = get_logger(__name__)


def get_search_config_repository(db=Depends(get_db)) -> SearchConfigRepository:
    """Dependency injection for SearchConfigRepository."""
    return SearchConfigRepository(db)


def get_search_execution_log_repository(
    db=Depends(get_db),
) -> SearchExecutionLogRepository:
    """Dependency injection for SearchExecutionLogRepository."""
    return SearchExecutionLogRepository(db)


def get_price_alert_repository(db=Depends(get_db)) -> PriceAlertRepository:
    return PriceAlertRepository(db)


def get_source_website_repository(db=Depends(get_db)) -> SourceWebsiteRepository:
    """Dependency injection for SourceWebsiteRepository (used by validator)."""
    return SourceWebsiteRepository(db)


def get_search_config_validator(
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
) -> SearchConfigValidator:
    """Dependency injection for SearchConfigValidator."""
    return SearchConfigValidator(search_config_repo, source_website_repo)


@router.post("/", response_model=SearchConfigReadResponse, status_code=201)
def create_search_config(
    search_config_in: SearchConfigCreateRequest,
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    search_config_validator: SearchConfigValidator = Depends(
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
        return SearchConfigPresenter.handle_validation_errors(validation_errors)

    attrs = search_config_in.data.attributes
    search_config_entity = SearchConfigEntity(
        search_term=attrs.search_term,
        is_active=attrs.is_active,
        frequency_days=attrs.frequency_days,
        preferred_time=attrs.preferred_time,
        search_metadata=attrs.search_metadata,
        user_id=attrs.user_id,
        source_website_ids=attrs.source_website_ids,
    )

    use_case = CreateSearchConfigUseCase(search_config_repo)
    created = use_case.execute(search_config_entity)

    logger.info(
        f"Search config created: '{created.search_term}' (ID: {created.id})",
        extra={
            "action": "search_config_created",
            "search_config_id": created.id,
            "user_id": current_user.id,
        },
    )
    return SearchConfigPresenter.handle_success(created)


@router.get("/", response_model=SearchConfigsCollectionResponse)
def list_search_configs(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default="desc", pattern="^(asc|desc)$"),
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    List all search configs with pagination. Regular users can only access their own search configs; staff can access all.

    Returns:
        - 200: Collection of search configs with pagination meta
        - 403: Permission denied
    """
    logger.debug(
        f"Listing search configs: limit={limit}, offset={offset}",
        extra={"action": "list_search_configs", "user_id": current_user.id},
    )

    use_case = ListSearchConfigsUseCase(search_config_repo)
    search_configs, total = use_case.execute(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        # Staff (incl. the Celery worker) see every config; users see their own.
        user_id=None if is_staff_or_superuser(current_user) else current_user.id,
    )
    return SearchConfigPresenter.handle_collection_success(search_configs, total)


@router.get("/user/{user_id}", response_model=SearchConfigsCollectionResponse)
def get_search_configs_by_user(
    user_id: int,
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
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

    use_case = GetSearchConfigsByUserIdUseCase(search_config_repo)
    if not can_access_owned_resource(user_id, current_user):
        raise HTTPException(
            status_code=403,
            detail="You can only list your own search configs.",
        )

    search_configs = use_case.execute(user_id)
    return SearchConfigPresenter.handle_collection_success(
        search_configs, len(search_configs)
    )


@router.get("/{search_config_id}", response_model=SearchConfigReadResponse)
def get_search_config(
    search_config_id: int,
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
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

    use_case = GetSearchConfigByIdUseCase(search_config_repo)
    search_config = use_case.execute(search_config_id)

    if not search_config or not can_access_owned_resource(
        search_config.user_id, current_user
    ):
        return SearchConfigPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    return SearchConfigPresenter.handle_success(search_config)


@router.put("/{search_config_id}", response_model=SearchConfigReadResponse)
def update_search_config(
    search_config_id: int,
    search_config_in: SearchConfigUpdateRequest,
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    search_config_validator: SearchConfigValidator = Depends(
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

    get_uc = GetSearchConfigByIdUseCase(search_config_repo)
    existing = get_uc.execute(search_config_id)

    if not existing or not can_access_owned_resource(existing.user_id, current_user):
        return SearchConfigPresenter.handle_not_found(
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
        return SearchConfigPresenter.handle_validation_errors(validation_errors)

    attrs = search_config_in.data.attributes
    updated_entity = SearchConfigEntity(
        id=search_config_id,
        search_term=attrs.search_term
        if attrs.search_term is not None
        else existing.search_term,
        is_active=attrs.is_active
        if attrs.is_active is not None
        else existing.is_active,
        frequency_days=attrs.frequency_days
        if attrs.frequency_days is not None
        else existing.frequency_days,
        preferred_time=attrs.preferred_time
        if attrs.preferred_time is not None
        else existing.preferred_time,
        search_metadata=attrs.search_metadata
        if attrs.search_metadata is not None
        else existing.search_metadata,
        user_id=existing.user_id,
        source_website_ids=attrs.source_website_ids
        if attrs.source_website_ids is not None
        else existing.source_website_ids,
    )

    update_uc = UpdateSearchConfigUseCase(search_config_repo)
    updated = update_uc.execute(search_config_id, updated_entity)

    logger.info(
        f"Search config updated: '{updated.search_term}' (ID: {search_config_id})",
        extra={
            "action": "search_config_updated",
            "search_config_id": search_config_id,
            "user_id": current_user.id,
        },
    )
    return SearchConfigPresenter.handle_success(updated)


@router.delete("/{search_config_id}", status_code=204)
def delete_search_config(
    search_config_id: int,
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Delete a search config. Requires staff or superuser access (regular users get search configs through their price alerts).

    Returns:
        - 204: Deleted successfully (no content)
        - 403: Permission denied
        - 404: Search config not found
    """
    logger.warning(
        f"Deleting search config ID: {search_config_id}",
        extra={
            "action": "delete_search_config",
            "search_config_id": search_config_id,
            "user_id": current_user.id,
        },
    )

    get_uc = GetSearchConfigByIdUseCase(search_config_repo)
    search_config = get_uc.execute(search_config_id)

    if not search_config or not can_access_owned_resource(
        search_config.user_id, current_user
    ):
        return SearchConfigPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    delete_uc = DeleteSearchConfigUseCase(search_config_repo)
    deleted = delete_uc.execute(search_config_id)

    if not deleted:
        return SearchConfigPresenter.handle_not_found(
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
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    log_repo: SearchExecutionLogRepository = Depends(
        get_search_execution_log_repository
    ),
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    plan_limits: PlanLimits = Depends(get_user_plan_limits),
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
    from src.app.use_cases.search_config_use_cases import GetSearchConfigByIdUseCase

    get_uc = GetSearchConfigByIdUseCase(search_config_repo)
    search_config = get_uc.execute(search_config_id)

    if not search_config or not can_access_owned_resource(
        search_config.user_id, current_user
    ):
        return SearchConfigPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    # Prevent concurrent runs: check latest log status
    latest_log = log_repo.get_latest_by_search_config_id(search_config_id)

    if not is_staff_or_superuser(current_user):
        linked_alerts = [
            alert
            for alert in price_alert_repo.get_by_user_id(current_user.id)
            if alert.search_config_id == search_config_id and alert.is_active
        ]
        if not linked_alerts:
            return SearchConfigPresenter.handle_not_found(
                f"id {search_config_id}", "/data/id"
            )
        violation = source_limit_violation(
            len(search_config.source_website_ids), plan_limits
        )
        if violation is None and not (
            latest_log and latest_log.status in ("pending", "running")
        ):
            violation = manual_run_violation(
                latest_log.started_at if latest_log else None,
                datetime.now(UTC),
                plan_limits,
            )
        if violation:
            return JSONResponse(
                status_code=403,
                content=JsonApiErrorResponse(
                    errors=[to_jsonapi_error(violation)]
                ).model_dump(),
                media_type="application/vnd.api+json",
            )

    if latest_log and latest_log.status in ("pending", "running"):
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

    task_id = dispatch_scraper_search(search_config_id)

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
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    log_repo: SearchExecutionLogRepository = Depends(
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
    from src.app.use_cases.search_config_use_cases import GetSearchConfigByIdUseCase

    get_uc = GetSearchConfigByIdUseCase(search_config_repo)
    search_config = get_uc.execute(search_config_id)

    if not search_config or not can_access_owned_resource(
        search_config.user_id, current_user
    ):
        return SearchConfigPresenter.handle_not_found(
            f"id {search_config_id}", "/data/id"
        )

    latest_log = log_repo.get_latest_by_search_config_id(search_config_id)

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
                "error_message": latest_log.error_message,
            },
        }
    }
