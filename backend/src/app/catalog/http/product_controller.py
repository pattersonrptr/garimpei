from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.app.alerts.persistence.mailer import EmailServiceMailer
from src.app.alerts.persistence.owners import UserAccountOwners
from src.app.alerts.persistence.repositories import (
    NotificationLogRepository,
    PriceAlertRepository,
)
from src.app.alerts.persistence.stores import SourceWebsiteStores
from src.app.alerts.use_cases import (
    EvaluateProductAlertsUseCase,
)
from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.entities import ProductListFilters
from src.app.catalog.http.product_presenter import ProductPresenter
from src.app.catalog.http.product_schema import (
    ProductCreateRequest,
    ProductReadResponse,
    ProductsCollectionResponse,
    ProductUpdateRequest,
)
from src.app.catalog.http.validators import ProductValidator
from src.app.catalog.persistence.repositories import (
    PriceHistoryRepository,
    ProductRepository,
)
from src.app.catalog.use_cases import (
    CreateProductUseCase,
    DeleteProductUseCase,
    GetProductByIdUseCase,
    GetProductByUrlUseCase,
    ListProductsUseCase,
    UpdateProductUseCase,
)
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.source_website_repository import (
    SourceWebsiteRepository,
)
from src.app.infrastructure.repositories.user_repository import UserRepository
from src.app.infrastructure.services.email_service import get_email_service
from src.app.interfaces.services.email_service import EmailServiceInterface
from src.app.security.auth import (
    get_current_active_user,
    get_current_staff_user,
    is_staff_or_superuser,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse
from src.config.logging_config import get_logger

router = APIRouter(tags=["products"], prefix="/products")

logger = get_logger(__name__)


def get_product_repository(db=Depends(get_db)) -> ProductRepository:
    """Dependency injection for ProductRepository."""
    return ProductRepository(db)


def get_product_validator(
    product_repo: ProductRepository = Depends(get_product_repository),
) -> ProductValidator:
    """Dependency injection for ProductValidator."""
    return ProductValidator(product_repo)


def get_price_alert_repository(db=Depends(get_db)) -> PriceAlertRepository:
    return PriceAlertRepository(db)


def get_price_history_repository(db=Depends(get_db)) -> PriceHistoryRepository:
    return PriceHistoryRepository(db)


def get_notification_log_repository(db=Depends(get_db)) -> NotificationLogRepository:
    return NotificationLogRepository(db)


def get_user_repository(db=Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_source_website_repository(db=Depends(get_db)) -> SourceWebsiteRepository:
    return SourceWebsiteRepository(db)


@router.post("/", response_model=ProductReadResponse, status_code=201)
def create_product(
    product_in: ProductCreateRequest,
    product_repo: ProductRepository = Depends(get_product_repository),
    product_validator: ProductValidator = Depends(get_product_validator),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Create a new product. Requires staff or superuser access.

    Returns:
        - 201: Product created successfully
        - 400: Validation errors
        - 403: Permission denied
        - 409: Product with same URL already exists
        - 422: Invalid field values
    """
    logger.info(
        f"Creating new product: {product_in.data.attributes.title}",
        extra={"action": "create_product", "user_id": current_user.id},
    )

    # Validate the request
    validation_errors = product_validator.validate_create_request(product_in)
    if validation_errors:
        logger.warning(
            f"Product creation validation failed: {len(validation_errors)} errors",
            extra={"action": "product_validation_failed", "user_id": current_user.id},
        )
        return ProductPresenter.handle_validation_errors(validation_errors)

    attrs = product_in.data.attributes
    product_entity = ProductEntity(
        url=attrs.url,
        title=attrs.title,
        source_product_code=attrs.source_product_code,
        description=attrs.description,
        image_urls=attrs.image_urls,
        city=attrs.city,
        state=attrs.state,
        condition=attrs.condition,
        seller_name=attrs.seller_name,
        is_available=attrs.is_available,
        source_website_id=attrs.source_website_id,
        source_metadata=attrs.source_metadata,
    )

    use_case = CreateProductUseCase(product_repo)
    created_product = use_case.execute(product_entity)

    logger.info(
        f"Product created successfully: {created_product.title} (ID: {created_product.id})",
        extra={
            "action": "product_created",
            "product_id": created_product.id,
            "user_id": current_user.id,
        },
    )

    return ProductPresenter.handle_success(created_product)


@router.get("/", response_model=ProductsCollectionResponse)
def list_products(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default="desc", pattern="^(asc|desc)$"),
    title: str | None = Query(default=None, max_length=255),
    condition: str | None = Query(
        default=None, pattern="^(new|used|refurbished|undetermined)$"
    ),
    is_available: bool | None = Query(default=None),
    source_website_id: int | None = Query(default=None),
    opportunities_only: bool = Query(default=False),
    product_repo: ProductRepository = Depends(get_product_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    List products with pagination, sorting and filters.

    Regular users see the listings their own alerts found (search term in the
    title, from one of the alert's sources). Staff see the whole catalog, and
    with ``opportunities_only`` the listings under one of their own alerts.

    Query Parameters:
        - limit: Maximum number of products to return (1-100, default: 10)
        - offset: Number of products to skip (default: 0)
        - sort_by: Field name to sort by (e.g., 'title', 'created_at')
        - sort_order: Sort order 'asc' or 'desc' (default: 'desc')
        - title: Text in the title (ignores case and accents)
        - condition: new, used, refurbished or undetermined
        - is_available: true or false
        - source_website_id: Only listings from this site
        - opportunities_only: Only listings at or below an alert's max price

    Returns:
        - 200: Collection of products with pagination meta
        - 403: Permission denied
    """
    logger.debug(
        f"Listing products: limit={limit}, offset={offset}, sort_by={sort_by}, sort_order={sort_order}",
        extra={"action": "list_products", "user_id": current_user.id},
    )

    sees_catalog = is_staff_or_superuser(current_user)
    filters = ProductListFilters(
        title=title.strip() if title and title.strip() else None,
        condition=condition,
        is_available=is_available,
        source_website_id=source_website_id,
        matching_user_id=None
        if sees_catalog and not opportunities_only
        else current_user.id,
        opportunities_only=opportunities_only,
    )
    use_case = ListProductsUseCase(product_repo)
    products, total = use_case.execute(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        filters=filters,
    )

    return ProductPresenter.handle_collection_success(products, total)


@router.get("/url", response_model=ProductReadResponse)
def get_product_by_url(
    url: str = Query(..., description="Product URL to search for"),
    product_repo: ProductRepository = Depends(get_product_repository),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Get a product by its URL. Requires staff or superuser access.

    Returns:
        - 200: Product found
        - 403: Permission denied
        - 404: Product not found
    """
    logger.debug(
        f"Getting product by URL: {url}",
        extra={"action": "get_product_by_url", "user_id": current_user.id},
    )

    use_case = GetProductByUrlUseCase(product_repo)
    product = use_case.execute(url)

    if not product:
        logger.debug(f"Product not found with URL: {url}")
        return ProductPresenter.handle_not_found(f"URL '{url}'", "/url")

    return ProductPresenter.handle_success(product)


@router.get("/{product_id}", response_model=ProductReadResponse)
def get_product(
    product_id: int,
    product_repo: ProductRepository = Depends(get_product_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get a single product by ID. Requires staff or superuser access.

    Returns:
        - 200: Product found
        - 403: Permission denied
        - 404: Product not found
    """
    logger.debug(
        f"Getting product ID: {product_id}",
        extra={
            "action": "get_product",
            "product_id": product_id,
            "user_id": current_user.id,
        },
    )

    use_case = GetProductByIdUseCase(product_repo)
    product = use_case.execute(product_id)

    if not product:
        logger.debug(f"Product not found: ID {product_id}")
        return ProductPresenter.handle_not_found(f"id {product_id}", "/data/id")

    return ProductPresenter.handle_success(product)


@router.put("/{product_id}", response_model=ProductReadResponse)
def update_product(
    product_id: int,
    product_in: ProductUpdateRequest,
    product_repo: ProductRepository = Depends(get_product_repository),
    product_validator: ProductValidator = Depends(get_product_validator),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Update an existing product. Requires staff or superuser access.

    Returns:
        - 200: Product updated successfully
        - 400: Validation errors
        - 403: Permission denied
        - 404: Product not found
        - 409: Duplicate URL conflict
        - 422: Invalid field values
    """
    logger.info(
        f"Updating product ID: {product_id}",
        extra={
            "action": "update_product",
            "product_id": product_id,
            "user_id": current_user.id,
        },
    )

    # Check if product exists
    get_product_uc = GetProductByIdUseCase(product_repo)
    existing_product = get_product_uc.execute(product_id)

    if not existing_product:
        logger.warning(f"Product not found for update: ID {product_id}")
        return ProductPresenter.handle_not_found(f"id {product_id}", "/data/id")

    # Validate the request
    validation_errors = product_validator.validate_update_request(
        product_id, product_in
    )
    if validation_errors:
        logger.warning(
            f"Product update validation failed: {len(validation_errors)} errors",
            extra={
                "action": "product_update_validation_failed",
                "product_id": product_id,
            },
        )
        return ProductPresenter.handle_validation_errors(validation_errors)

    # Create entity with updated data
    attrs = product_in.data.attributes
    product_entity = ProductEntity(
        id=product_id,
        url=attrs.url if attrs.url is not None else existing_product.url,
        title=attrs.title if attrs.title is not None else existing_product.title,
        source_product_code=attrs.source_product_code
        if attrs.source_product_code is not None
        else existing_product.source_product_code,
        description=attrs.description
        if attrs.description is not None
        else existing_product.description,
        image_urls=attrs.image_urls
        if attrs.image_urls is not None
        else existing_product.image_urls,
        city=attrs.city if attrs.city is not None else existing_product.city,
        state=attrs.state if attrs.state is not None else existing_product.state,
        condition=attrs.condition
        if attrs.condition is not None
        else existing_product.condition,
        seller_name=attrs.seller_name
        if attrs.seller_name is not None
        else existing_product.seller_name,
        is_available=attrs.is_available
        if attrs.is_available is not None
        else existing_product.is_available,
        source_website_id=attrs.source_website_id
        if attrs.source_website_id is not None
        else existing_product.source_website_id,
        source_metadata=attrs.source_metadata
        if attrs.source_metadata is not None
        else existing_product.source_metadata,
    )

    update_uc = UpdateProductUseCase(product_repo)
    updated_product = update_uc.execute(product_id, product_entity)

    logger.info(
        f"Product updated successfully: {updated_product.title} (ID: {product_id})",
        extra={
            "action": "product_updated",
            "product_id": product_id,
            "user_id": current_user.id,
        },
    )

    return ProductPresenter.handle_success(updated_product)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    product_repo: ProductRepository = Depends(get_product_repository),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Delete a product. Requires staff or superuser access.

    Returns:
        - 204: Product deleted successfully (no content)
        - 403: Permission denied
        - 404: Product not found
    """
    logger.warning(
        f"Deleting product ID: {product_id}",
        extra={
            "action": "delete_product",
            "product_id": product_id,
            "user_id": current_user.id,
        },
    )

    # Check if product exists
    get_product_uc = GetProductByIdUseCase(product_repo)
    product = get_product_uc.execute(product_id)

    if not product:
        logger.warning(f"Product not found for deletion: ID {product_id}")
        return ProductPresenter.handle_not_found(f"id {product_id}", "/data/id")

    delete_uc = DeleteProductUseCase(product_repo)
    deleted = delete_uc.execute(product_id)

    if not deleted:
        logger.error(f"Failed to delete product ID: {product_id}")
        return ProductPresenter.handle_not_found(f"id {product_id}", "/data/id")

    logger.warning(
        f"Product deleted successfully: {product.title} (ID: {product_id})",
        extra={
            "action": "product_deleted",
            "product_id": product_id,
            "user_id": current_user.id,
        },
    )

    return None


@router.post("/{product_id}/evaluate-alerts", status_code=200)
def evaluate_product_alerts(
    product_id: int,
    product_repo: ProductRepository = Depends(get_product_repository),
    price_history_repo: PriceHistoryRepository = Depends(get_price_history_repository),
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    notification_log_repo: NotificationLogRepository = Depends(
        get_notification_log_repository
    ),
    user_repo: UserRepository = Depends(get_user_repository),
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
    email_service: EmailServiceInterface = Depends(get_email_service),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Evaluate all active price alerts against a specific product.

    After a product is created/updated, call this endpoint to automatically
    find matching PriceAlerts and trigger email notifications.

    Dedup: if a notification was already sent for the same product + alert
    pair, it will be skipped.

    Requires staff or superuser access.

    Returns:
        - 200: Evaluation result with counts
        - 404: Product not found
    """
    logger.info(
        f"Evaluating alerts for product ID: {product_id}",
        extra={
            "action": "evaluate_product_alerts",
            "product_id": product_id,
            "user_id": current_user.id,
        },
    )

    use_case = EvaluateProductAlertsUseCase(
        product_repo=product_repo,
        price_history_repo=price_history_repo,
        price_alert_repo=price_alert_repo,
        notification_log_repo=notification_log_repo,
        user_repo=UserAccountOwners(user_repo),
        source_website_repo=SourceWebsiteStores(source_website_repo),
        email_service=EmailServiceMailer(email_service),
    )
    sent_logs, skipped, error = use_case.execute(product_id)

    if error:
        if "not found" in error.lower():
            return JSONResponse(
                status_code=404,
                content=JsonApiErrorResponse(
                    errors=[
                        JsonApiError(
                            status="404",
                            code="NOT_FOUND",
                            title="Product not found",
                            detail=error,
                            source={"pointer": "/data/id"},
                        )
                    ]
                ).model_dump(),
                media_type="application/vnd.api+json",
            )
        # Non-error skip reasons (no price, no matching alerts)
        return {
            "data": {
                "type": "evaluate_alerts_results",
                "attributes": {
                    "status": "skipped",
                    "message": error,
                    "notifications_sent": 0,
                    "skipped": 0,
                },
            }
        }

    sent_count = len(sent_logs)
    return {
        "data": {
            "type": "evaluate_alerts_results",
            "attributes": {
                "status": "sent" if sent_count > 0 else "no_matches",
                "message": (
                    f"{sent_count} notification(s) sent, {skipped} skipped (dedup)"
                ),
                "notifications_sent": sent_count,
                "skipped": skipped,
            },
        }
    }
