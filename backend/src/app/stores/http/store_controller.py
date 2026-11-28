from fastapi import APIRouter, Depends, Query

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import get_current_active_user, get_current_staff_user
from src.app.infrastructure.database_config import get_db
from src.app.stores import wiring
from src.app.stores.entities import Store
from src.app.stores.http.store_presenter import (
    StorePresenter,
)
from src.app.stores.http.store_schema import (
    StoreCreateRequest,
    StoreReadResponse,
    StoresCollectionResponse,
    StoreUpdateRequest,
)
from src.app.stores.http.validators import StoreValidator
from src.app.stores.ports import StoreRepositoryInterface
from src.app.stores.use_cases import (
    CreateStoreUseCase,
    DeleteStoreUseCase,
    GetStoreByNameUseCase,
    GetStoreUseCase,
    ListStoresUseCase,
    StoreChanges,
    StoreHasOffersError,
    StoreNotFoundError,
    UpdateStoreUseCase,
)
from src.config.logging_config import get_logger

router = APIRouter(tags=["source_websites"], prefix="/source-websites")

logger = get_logger(__name__)


def get_source_website_repository(db=Depends(get_db)) -> StoreRepositoryInterface:
    """Stores' repository, built by stores/wiring.py."""
    return wiring.stores(db)


def get_source_website_validator(
    source_website_repo: StoreRepositoryInterface = Depends(
        get_source_website_repository
    ),
) -> StoreValidator:
    """Dependency injection for StoreValidator."""
    return StoreValidator(source_website_repo)


def _not_found_by_id(store_id: int):
    return StorePresenter.handle_not_found(f"id {store_id}", "/data/id")


@router.post("/", response_model=StoreReadResponse, status_code=201)
def create_source_website(
    source_website_in: StoreCreateRequest,
    source_website_repo: StoreRepositoryInterface = Depends(
        get_source_website_repository
    ),
    source_website_validator: StoreValidator = Depends(get_source_website_validator),
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
        return StorePresenter.handle_validation_errors(validation_errors)

    attrs = source_website_in.data.attributes
    created = CreateStoreUseCase(source_website_repo).execute(
        Store(name=attrs.name, base_url=attrs.base_url, is_active=attrs.is_active)
    )

    logger.info(
        f"Source website created successfully: {created.name} (ID: {created.id})",
        extra={
            "action": "source_website_created",
            "source_website_id": created.id,
            "user_id": current_user.id,
        },
    )
    return StorePresenter.handle_success(created)


@router.get("/", response_model=StoresCollectionResponse)
def list_source_websites(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default="desc", pattern="^(asc|desc)$"),
    source_website_repo: StoreRepositoryInterface = Depends(
        get_source_website_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    List all source websites with pagination and sorting.

    Returns:
        - 200: Collection of source websites with pagination meta
    """
    logger.debug(
        f"Listing source websites: limit={limit}, offset={offset}",
        extra={"action": "list_source_websites", "user_id": current_user.id},
    )

    stores, total = ListStoresUseCase(source_website_repo).execute(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return StorePresenter.handle_collection_success(stores, total)


@router.get("/name/{name}", response_model=StoreReadResponse)
def get_source_website_by_name(
    name: str,
    source_website_repo: StoreRepositoryInterface = Depends(
        get_source_website_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get a source website by its name.

    Returns:
        - 200: Source website found
        - 404: Source website not found
    """
    logger.debug(
        f"Getting source website by name: {name}",
        extra={"action": "get_source_website_by_name", "user_id": current_user.id},
    )

    try:
        store = GetStoreByNameUseCase(source_website_repo).execute(name)
    except StoreNotFoundError:
        return StorePresenter.handle_not_found(f"name '{name}'", "/name")
    return StorePresenter.handle_success(store)


@router.get("/{source_website_id}", response_model=StoreReadResponse)
def get_source_website(
    source_website_id: int,
    source_website_repo: StoreRepositoryInterface = Depends(
        get_source_website_repository
    ),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get a single source website by ID.

    Returns:
        - 200: Source website found
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

    try:
        store = GetStoreUseCase(source_website_repo).execute(source_website_id)
    except StoreNotFoundError:
        return _not_found_by_id(source_website_id)
    return StorePresenter.handle_success(store)


@router.put("/{source_website_id}", response_model=StoreReadResponse)
def update_source_website(
    source_website_id: int,
    source_website_in: StoreUpdateRequest,
    source_website_repo: StoreRepositoryInterface = Depends(
        get_source_website_repository
    ),
    source_website_validator: StoreValidator = Depends(get_source_website_validator),
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

    # A missing store answers 404 before the body is validated.
    try:
        GetStoreUseCase(source_website_repo).execute(source_website_id)
    except StoreNotFoundError:
        return _not_found_by_id(source_website_id)

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
        return StorePresenter.handle_validation_errors(validation_errors)

    attrs = source_website_in.data.attributes
    changes = StoreChanges(
        name=attrs.name, base_url=attrs.base_url, is_active=attrs.is_active
    )
    try:
        updated = UpdateStoreUseCase(source_website_repo).execute(
            source_website_id, changes
        )
    except StoreNotFoundError:
        return _not_found_by_id(source_website_id)

    logger.info(
        f"Source website updated successfully: {updated.name} (ID: {source_website_id})",
        extra={
            "action": "source_website_updated",
            "source_website_id": source_website_id,
            "user_id": current_user.id,
        },
    )
    return StorePresenter.handle_success(updated)


@router.delete("/{source_website_id}", status_code=204)
def delete_source_website(
    source_website_id: int,
    source_website_repo: StoreRepositoryInterface = Depends(
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
        - 409: The source website still has offers
    """
    logger.warning(
        f"Deleting source website ID: {source_website_id}",
        extra={
            "action": "delete_source_website",
            "source_website_id": source_website_id,
            "user_id": current_user.id,
        },
    )

    try:
        DeleteStoreUseCase(source_website_repo).execute(source_website_id)
    except StoreNotFoundError:
        return _not_found_by_id(source_website_id)
    except StoreHasOffersError:
        return StorePresenter.handle_has_offers()

    logger.warning(
        f"Source website deleted (ID: {source_website_id})",
        extra={
            "action": "source_website_deleted",
            "source_website_id": source_website_id,
            "user_id": current_user.id,
        },
    )
    return None
