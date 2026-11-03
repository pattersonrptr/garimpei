from fastapi import APIRouter, Depends, Query

from src.app.domain.validators.source_website_validator import SourceWebsiteValidator
from src.app.entities.source_website import SourceWebsite as SourceWebsiteEntity
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.source_website_repository import (
    SourceWebsiteRepository,
)
from src.app.interfaces.http.presenters.source_website_presenter import (
    SourceWebsitePresenter,
)
from src.app.interfaces.http.schemas.source_website_schema import (
    SourceWebsiteCreateRequest,
    SourceWebsiteReadResponse,
    SourceWebsitesCollectionResponse,
    SourceWebsiteUpdateRequest,
)
from src.app.security.auth import get_current_active_user, get_current_staff_user
from src.app.use_cases.source_website_use_cases import (
    CreateSourceWebsiteUseCase,
    DeleteSourceWebsiteUseCase,
    GetSourceWebsiteByIdUseCase,
    GetSourceWebsiteByNameUseCase,
    ListSourceWebsitesUseCase,
    UpdateSourceWebsiteUseCase,
)
from src.config.logging_config import get_logger

router = APIRouter(tags=["source_websites"], prefix="/source-websites")

logger = get_logger(__name__)


def get_source_website_repository(db=Depends(get_db)) -> SourceWebsiteRepository:
    """Dependency injection for SourceWebsiteRepository."""
    return SourceWebsiteRepository(db)


def get_source_website_validator(
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
) -> SourceWebsiteValidator:
    """Dependency injection for SourceWebsiteValidator."""
    return SourceWebsiteValidator(source_website_repo)


@router.post("/", response_model=SourceWebsiteReadResponse, status_code=201)
def create_source_website(
    source_website_in: SourceWebsiteCreateRequest,
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
    source_website_validator: SourceWebsiteValidator = Depends(
        get_source_website_validator
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Create a new source website. Requires staff or superuser access.

    Returns:
        - 201: Source website created successfully
        - 400: Validation errors
        - 403: Permission denied
        - 409: Source website with same name already exists
        - 422: Invalid field values
    """
    logger.info(
        f"Creating new source website: {source_website_in.data.attributes.name}",
        extra={"action": "create_source_website", "user_id": current_user.id},
    )

    validation_errors = source_website_validator.validate_create_request(
        source_website_in
    )
    if validation_errors:
        logger.warning(
            f"Source website creation validation failed: {len(validation_errors)} errors",
            extra={
                "action": "source_website_validation_failed",
                "user_id": current_user.id,
            },
        )
        return SourceWebsitePresenter.handle_validation_errors(validation_errors)

    attrs = source_website_in.data.attributes
    source_website_entity = SourceWebsiteEntity(
        name=attrs.name,
        base_url=attrs.base_url,
        is_active=attrs.is_active,
    )

    use_case = CreateSourceWebsiteUseCase(source_website_repo)
    created = use_case.execute(source_website_entity)

    logger.info(
        f"Source website created successfully: {created.name} (ID: {created.id})",
        extra={
            "action": "source_website_created",
            "source_website_id": created.id,
            "user_id": current_user.id,
        },
    )
    return SourceWebsitePresenter.handle_success(created)


@router.get("/", response_model=SourceWebsitesCollectionResponse)
def list_source_websites(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default="desc", pattern="^(asc|desc)$"),
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    List all source websites with pagination and sorting. Requires staff or superuser access.

    Returns:
        - 200: Collection of source websites with pagination meta
        - 403: Permission denied
    """
    logger.debug(
        f"Listing source websites: limit={limit}, offset={offset}",
        extra={"action": "list_source_websites", "user_id": current_user.id},
    )

    use_case = ListSourceWebsitesUseCase(source_website_repo)
    source_websites, total = use_case.execute(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return SourceWebsitePresenter.handle_collection_success(source_websites, total)


@router.get("/name/{name}", response_model=SourceWebsiteReadResponse)
def get_source_website_by_name(
    name: str,
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get a source website by its name. Requires staff or superuser access.

    Returns:
        - 200: Source website found
        - 403: Permission denied
        - 404: Source website not found
    """
    logger.debug(
        f"Getting source website by name: {name}",
        extra={"action": "get_source_website_by_name", "user_id": current_user.id},
    )

    use_case = GetSourceWebsiteByNameUseCase(source_website_repo)
    source_website = use_case.execute(name)

    if not source_website:
        return SourceWebsitePresenter.handle_not_found(f"name '{name}'", "/name")

    return SourceWebsitePresenter.handle_success(source_website)


@router.get("/{source_website_id}", response_model=SourceWebsiteReadResponse)
def get_source_website(
    source_website_id: int,
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get a single source website by ID. Requires staff or superuser access.

    Returns:
        - 200: Source website found
        - 403: Permission denied
        - 404: Source website not found
    """
    logger.debug(
        f"Getting source website ID: {source_website_id}",
        extra={
            "action": "get_source_website",
            "source_website_id": source_website_id,
            "user_id": current_user.id,
        },
    )

    use_case = GetSourceWebsiteByIdUseCase(source_website_repo)
    source_website = use_case.execute(source_website_id)

    if not source_website:
        return SourceWebsitePresenter.handle_not_found(
            f"id {source_website_id}", "/data/id"
        )

    return SourceWebsitePresenter.handle_success(source_website)


@router.put("/{source_website_id}", response_model=SourceWebsiteReadResponse)
def update_source_website(
    source_website_id: int,
    source_website_in: SourceWebsiteUpdateRequest,
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
    source_website_validator: SourceWebsiteValidator = Depends(
        get_source_website_validator
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Update an existing source website. Requires staff or superuser access.

    Returns:
        - 200: Source website updated successfully
        - 400: Validation errors
        - 403: Permission denied
        - 404: Source website not found
        - 409: Duplicate name conflict
        - 422: Invalid field values
    """
    logger.info(
        f"Updating source website ID: {source_website_id}",
        extra={
            "action": "update_source_website",
            "source_website_id": source_website_id,
            "user_id": current_user.id,
        },
    )

    # Check if source website exists
    get_uc = GetSourceWebsiteByIdUseCase(source_website_repo)
    existing = get_uc.execute(source_website_id)

    if not existing:
        return SourceWebsitePresenter.handle_not_found(
            f"id {source_website_id}", "/data/id"
        )

    # Validate
    validation_errors = source_website_validator.validate_update_request(
        source_website_id, source_website_in
    )
    if validation_errors:
        logger.warning(
            f"Source website update validation failed: {len(validation_errors)} errors",
            extra={
                "action": "source_website_update_validation_failed",
                "source_website_id": source_website_id,
            },
        )
        return SourceWebsitePresenter.handle_validation_errors(validation_errors)

    attrs = source_website_in.data.attributes
    source_website_entity = SourceWebsiteEntity(
        id=source_website_id,
        name=attrs.name if attrs.name is not None else existing.name,
        base_url=attrs.base_url if attrs.base_url is not None else existing.base_url,
        is_active=attrs.is_active
        if attrs.is_active is not None
        else existing.is_active,
    )

    update_uc = UpdateSourceWebsiteUseCase(source_website_repo)
    updated = update_uc.execute(source_website_id, source_website_entity)

    logger.info(
        f"Source website updated successfully: {updated.name} (ID: {source_website_id})",
        extra={
            "action": "source_website_updated",
            "source_website_id": source_website_id,
            "user_id": current_user.id,
        },
    )
    return SourceWebsitePresenter.handle_success(updated)


@router.delete("/{source_website_id}", status_code=204)
def delete_source_website(
    source_website_id: int,
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Delete a source website. Requires staff or superuser access.

    Returns:
        - 204: Deleted successfully (no content)
        - 403: Permission denied
        - 404: Source website not found
    """
    logger.warning(
        f"Deleting source website ID: {source_website_id}",
        extra={
            "action": "delete_source_website",
            "source_website_id": source_website_id,
            "user_id": current_user.id,
        },
    )

    get_uc = GetSourceWebsiteByIdUseCase(source_website_repo)
    source_website = get_uc.execute(source_website_id)

    if not source_website:
        return SourceWebsitePresenter.handle_not_found(
            f"id {source_website_id}", "/data/id"
        )

    delete_uc = DeleteSourceWebsiteUseCase(source_website_repo)
    deleted = delete_uc.execute(source_website_id)

    if not deleted:
        return SourceWebsitePresenter.handle_not_found(
            f"id {source_website_id}", "/data/id"
        )

    logger.warning(
        f"Source website deleted: {source_website.name} (ID: {source_website_id})",
        extra={
            "action": "source_website_deleted",
            "source_website_id": source_website_id,
            "user_id": current_user.id,
        },
    )
    return None
