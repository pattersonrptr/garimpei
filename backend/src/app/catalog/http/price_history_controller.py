from fastapi import APIRouter, Depends, Query

from src.app.catalog.entities import PriceHistory as PriceHistoryEntity
from src.app.catalog.http.price_history_presenter import (
    PriceHistoryPresenter,
)
from src.app.catalog.http.price_history_schema import (
    PriceHistoriesCollectionResponse,
    PriceHistoryCreateRequest,
    PriceHistoryReadResponse,
)
from src.app.catalog.persistence.repositories import (
    PriceHistoryRepository,
    ProductRepository,
)
from src.app.catalog.rules import PriceHistoryValidator
from src.app.catalog.use_cases import (
    CreatePriceHistoryUseCase,
    DeletePriceHistoryUseCase,
    GetLatestPriceByProductIdUseCase,
    GetPriceHistoryByIdUseCase,
    GetPriceHistoryByProductIdUseCase,
    ListPriceHistoriesUseCase,
)
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.security.auth import get_current_active_user, get_current_staff_user
from src.config.logging_config import get_logger

router = APIRouter(tags=["price_histories"], prefix="/price-histories")

logger = get_logger(__name__)


def get_price_history_repository(db=Depends(get_db)) -> PriceHistoryRepository:
    """Dependency injection for PriceHistoryRepository."""
    return PriceHistoryRepository(db)


def get_product_repository(db=Depends(get_db)) -> ProductRepository:
    """Dependency injection for ProductRepository (used by validator)."""
    return ProductRepository(db)


def get_price_history_validator(
    price_history_repo: PriceHistoryRepository = Depends(get_price_history_repository),
    product_repo: ProductRepository = Depends(get_product_repository),
) -> PriceHistoryValidator:
    """Dependency injection for PriceHistoryValidator."""
    return PriceHistoryValidator(price_history_repo, product_repo)


@router.post("/", response_model=PriceHistoryReadResponse, status_code=201)
def create_price_history(
    price_history_in: PriceHistoryCreateRequest,
    price_history_repo: PriceHistoryRepository = Depends(get_price_history_repository),
    price_history_validator: PriceHistoryValidator = Depends(
        get_price_history_validator
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Record a new price entry for a product. Requires staff or superuser access.

    Returns:
        - 201: Price history record created successfully
        - 400: Validation errors (invalid type)
        - 403: Permission denied
        - 404: Referenced product not found
        - 422: Invalid field values
    """
    logger.info(
        f"Recording price history for product_id: {price_history_in.data.attributes.product_id}",
        extra={"action": "create_price_history", "user_id": current_user.id},
    )

    validation_errors = price_history_validator.validate_create_request(
        price_history_in
    )
    if validation_errors:
        logger.warning(
            f"Price history creation validation failed: {len(validation_errors)} errors",
            extra={
                "action": "price_history_validation_failed",
                "user_id": current_user.id,
            },
        )
        return PriceHistoryPresenter.handle_validation_errors(validation_errors)

    attrs = price_history_in.data.attributes
    price_history_entity = PriceHistoryEntity(
        product_id=attrs.product_id,
        price=attrs.price,
    )

    use_case = CreatePriceHistoryUseCase(price_history_repo)
    created = use_case.execute(price_history_entity)

    logger.info(
        f"Price history created: product_id={created.product_id}, price={created.price} (ID: {created.id})",
        extra={
            "action": "price_history_created",
            "price_history_id": created.id,
            "user_id": current_user.id,
        },
    )
    return PriceHistoryPresenter.handle_success(created)


@router.get("/", response_model=PriceHistoriesCollectionResponse)
def list_price_histories(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default="desc", pattern="^(asc|desc)$"),
    price_history_repo: PriceHistoryRepository = Depends(get_price_history_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    List all price history records with pagination. Requires staff or superuser access.

    Returns:
        - 200: Collection of price history records with pagination meta
        - 403: Permission denied
    """
    logger.debug(
        f"Listing price histories: limit={limit}, offset={offset}",
        extra={"action": "list_price_histories", "user_id": current_user.id},
    )

    use_case = ListPriceHistoriesUseCase(price_history_repo)
    records, total = use_case.execute(
        limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
    )
    return PriceHistoryPresenter.handle_collection_success(records, total)


@router.get("/product/{product_id}/latest", response_model=PriceHistoryReadResponse)
def get_latest_price_by_product(
    product_id: int,
    price_history_repo: PriceHistoryRepository = Depends(get_price_history_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get the most recent price record for a product. Requires staff or superuser access.

    Returns:
        - 200: Latest price history record
        - 403: Permission denied
        - 404: No price history found for the given product
    """
    logger.debug(
        f"Getting latest price for product_id: {product_id}",
        extra={"action": "get_latest_price", "user_id": current_user.id},
    )

    use_case = GetLatestPriceByProductIdUseCase(price_history_repo)
    record = use_case.execute(product_id)

    if not record:
        return PriceHistoryPresenter.handle_not_found(
            f"product_id {product_id}", "/data/attributes/product_id"
        )

    return PriceHistoryPresenter.handle_success(record)


@router.get("/product/{product_id}", response_model=PriceHistoriesCollectionResponse)
def get_price_history_by_product(
    product_id: int,
    price_history_repo: PriceHistoryRepository = Depends(get_price_history_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get all price records for a product. Requires staff or superuser access.

    Returns:
        - 200: Collection of price history records
        - 403: Permission denied
    """
    logger.debug(
        f"Getting price history for product_id: {product_id}",
        extra={"action": "get_price_history_by_product", "user_id": current_user.id},
    )

    use_case = GetPriceHistoryByProductIdUseCase(price_history_repo)
    records = use_case.execute(product_id)
    return PriceHistoryPresenter.handle_collection_success(records, len(records))


@router.get("/{price_history_id}", response_model=PriceHistoryReadResponse)
def get_price_history(
    price_history_id: int,
    price_history_repo: PriceHistoryRepository = Depends(get_price_history_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get a single price history record by ID. Requires staff or superuser access.

    Returns:
        - 200: Price history record found
        - 403: Permission denied
        - 404: Not found
    """
    logger.debug(
        f"Getting price history ID: {price_history_id}",
        extra={"action": "get_price_history", "user_id": current_user.id},
    )

    use_case = GetPriceHistoryByIdUseCase(price_history_repo)
    record = use_case.execute(price_history_id)

    if not record:
        return PriceHistoryPresenter.handle_not_found(
            f"id {price_history_id}", "/data/id"
        )

    return PriceHistoryPresenter.handle_success(record)


@router.delete("/{price_history_id}", status_code=204)
def delete_price_history(
    price_history_id: int,
    price_history_repo: PriceHistoryRepository = Depends(get_price_history_repository),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Delete a price history record. Requires staff or superuser access.

    Returns:
        - 204: Deleted successfully (no content)
        - 403: Permission denied
        - 404: Not found
    """
    logger.warning(
        f"Deleting price history ID: {price_history_id}",
        extra={"action": "delete_price_history", "user_id": current_user.id},
    )

    get_uc = GetPriceHistoryByIdUseCase(price_history_repo)
    record = get_uc.execute(price_history_id)

    if not record:
        return PriceHistoryPresenter.handle_not_found(
            f"id {price_history_id}", "/data/id"
        )

    delete_uc = DeletePriceHistoryUseCase(price_history_repo)
    delete_uc.execute(price_history_id)

    logger.warning(
        f"Price history deleted: ID={price_history_id}",
        extra={"action": "price_history_deleted", "user_id": current_user.id},
    )
    return None
