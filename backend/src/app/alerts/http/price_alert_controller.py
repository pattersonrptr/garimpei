from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.app.alerts.entities import PriceAlert as PriceAlertEntity
from src.app.alerts.http.price_alert_presenter import (
    PriceAlertPresenter,
)
from src.app.alerts.http.price_alert_schema import (
    PriceAlertCreateRequest,
    PriceAlertReadResponse,
    PriceAlertsCollectionResponse,
    PriceAlertUpdateRequest,
)
from src.app.alerts.http.validators import PriceAlertValidator
from src.app.alerts.persistence.book_finder import CatalogBookFinder
from src.app.alerts.persistence.keyword_searches import SearchConfigKeywordSearches
from src.app.alerts.persistence.listings import CatalogListings
from src.app.alerts.persistence.mailer import EmailServiceMailer
from src.app.alerts.persistence.owners import UserAccountOwners
from src.app.alerts.persistence.repositories import (
    NotificationLogRepository,
    PriceAlertRepository,
)
from src.app.alerts.persistence.stores import SourceWebsiteStores
from src.app.alerts.use_cases import (
    CreatePriceAlertUseCase,
    DeletePriceAlertUseCase,
    GetPriceAlertByIdUseCase,
    GetPriceAlertsByUserIdUseCase,
    GetProductsByPriceAlertUseCase,
    ListPriceAlertsUseCase,
    NotifyAlertOpportunitiesUseCase,
    SendPriceAlertNotificationUseCase,
    UpdatePriceAlertUseCase,
)
from src.app.catalog.http.product_presenter import ProductPresenter
from src.app.catalog.http.product_schema import ProductsCollectionResponse
from src.app.catalog.persistence.repositories import ProductRepository
from src.app.domain.plan_limits import PlanLimits
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.search_config_repository import (
    SearchConfigRepository,
)
from src.app.infrastructure.repositories.source_website_repository import (
    SourceWebsiteRepository,
)
from src.app.infrastructure.repositories.user_repository import UserRepository
from src.app.infrastructure.services.email_service import get_email_service
from src.app.interfaces.http.plan_limits import (
    check_alert_limit,
    check_frequency_limit,
    check_source_limit,
    get_user_plan_limits,
)
from src.app.interfaces.services.email_service import EmailServiceInterface
from src.app.security.auth import (
    can_access_owned_resource,
    get_current_active_user,
    get_current_staff_user,
    is_staff_or_superuser,
)
from src.common.jsonapi import JsonApiError, JsonApiErrorResponse
from src.config.logging_config import get_logger

router = APIRouter(tags=["price_alerts"], prefix="/price-alerts")

BOOK_ALERT_FREQUENCY = 1440  # minutes

logger = get_logger(__name__)


def get_price_alert_repository(db=Depends(get_db)) -> PriceAlertRepository:
    """Dependency injection for PriceAlertRepository."""
    return PriceAlertRepository(db)


def get_search_config_repository(db=Depends(get_db)) -> SearchConfigRepository:
    """Dependency injection for SearchConfigRepository."""
    return SearchConfigRepository(db)


def get_product_repository(db=Depends(get_db)) -> ProductRepository:
    """Dependency injection for ProductRepository."""
    return ProductRepository(db)


def get_source_website_repository(db=Depends(get_db)) -> SourceWebsiteRepository:
    """Dependency injection for SourceWebsiteRepository (used by validator)."""
    return SourceWebsiteRepository(db)


def get_user_repository(db=Depends(get_db)) -> UserRepository:
    """Dependency injection for UserRepository."""
    return UserRepository(db)


def get_notification_log_repository(
    db=Depends(get_db),
) -> NotificationLogRepository:
    """Dependency injection for NotificationLogRepository."""
    return NotificationLogRepository(db)


def get_alert_opportunities_use_case(
    db=Depends(get_db),
    email_service: EmailServiceInterface = Depends(get_email_service),
) -> NotifyAlertOpportunitiesUseCase:
    """The use case that checks collected listings when an alert changes."""
    return NotifyAlertOpportunitiesUseCase(
        product_repo=ProductRepository(db),
        price_alert_repo=PriceAlertRepository(db),
        notification_log_repo=NotificationLogRepository(db),
        user_repo=UserAccountOwners(UserRepository(db)),
        source_website_repo=SourceWebsiteStores(SourceWebsiteRepository(db)),
        email_service=EmailServiceMailer(email_service),
    )


def get_price_alert_validator(
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
    db=Depends(get_db),
) -> PriceAlertValidator:
    """Dependency injection for PriceAlertValidator."""
    return PriceAlertValidator(
        price_alert_repo,
        SourceWebsiteStores(source_website_repo),
        CatalogBookFinder(db),
    )


@router.post("/", response_model=PriceAlertReadResponse, status_code=201)
def create_price_alert(
    price_alert_in: PriceAlertCreateRequest,
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    price_alert_validator: PriceAlertValidator = Depends(get_price_alert_validator),
    current_user: UserEntity = Depends(get_current_active_user),
    plan_limits: PlanLimits = Depends(get_user_plan_limits),
    opportunities: NotifyAlertOpportunitiesUseCase = Depends(
        get_alert_opportunities_use_case
    ),
    db: Session = Depends(get_db),
):
    """
    Create a new price alert. Regular users can only access their own alerts; staff can access all.

    Automatically creates or reuses a SearchConfig matching the alert's
    search_term and source_website_ids for the same user.

    Returns:
        - 201: Price alert created successfully
        - 400: Validation errors (invalid type)
        - 403: Permission denied
        - 404: Referenced source website not found
        - 409: Duplicate search term for this user
        - 422: Invalid field values
    """
    logger.info(
        "Creating new price alert: "
        f"'{price_alert_in.data.attributes.search_term or price_alert_in.data.attributes.isbn}'",
        extra={"action": "create_price_alert", "user_id": current_user.id},
    )

    validation_errors = price_alert_validator.validate_create_request(price_alert_in)
    if validation_errors:
        logger.warning(
            f"Price alert creation validation failed: {len(validation_errors)} errors",
            extra={
                "action": "price_alert_validation_failed",
                "user_id": current_user.id,
            },
        )
        return PriceAlertPresenter.handle_validation_errors(validation_errors)

    attrs = price_alert_in.data.attributes

    # --- Plan limits enforcement ---
    alert_limit_err = check_alert_limit(db, current_user.id, plan_limits)
    if alert_limit_err:
        return PriceAlertPresenter.handle_validation_errors([alert_limit_err])

    # A book alert is checked whenever an offer for the book comes in, and
    # books are collected once a day: its frequency is always a day.
    frequency_minutes = BOOK_ALERT_FREQUENCY if attrs.isbn else attrs.frequency_minutes
    freq_err = check_frequency_limit(frequency_minutes, plan_limits)
    if freq_err:
        return PriceAlertPresenter.handle_validation_errors([freq_err])

    source_err = check_source_limit(len(attrs.source_website_ids), plan_limits)
    if source_err:
        return PriceAlertPresenter.handle_validation_errors([source_err])

    book = CatalogBookFinder(db).find_by_isbn(attrs.isbn) if attrs.isbn else None
    price_alert_entity = PriceAlertEntity(
        search_term=book.title[:255] if book else attrs.search_term,
        canonical_product_id=book.id if book else None,
        condition=(attrs.condition or "any") if book else None,
        max_price=attrs.max_price,
        is_active=attrs.is_active,
        frequency_minutes=frequency_minutes,
        # Regular users always own the alerts they create; staff may create
        # alerts on behalf of another user.
        user_id=attrs.user_id
        if is_staff_or_superuser(current_user)
        else current_user.id,
        source_website_ids=attrs.source_website_ids,
    )

    use_case = CreatePriceAlertUseCase(
        price_alert_repo, SearchConfigKeywordSearches(search_config_repo)
    )
    created = use_case.execute(price_alert_entity)
    opportunities.execute(created)

    logger.info(
        f"Price alert created: '{created.search_term}' (ID: {created.id})",
        extra={
            "action": "price_alert_created",
            "price_alert_id": created.id,
            "user_id": current_user.id,
        },
    )
    return PriceAlertPresenter.handle_success(created)


@router.get("/", response_model=PriceAlertsCollectionResponse)
def list_price_alerts(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default="desc", pattern="^(asc|desc)$"),
    scope: str = Query(default="mine", pattern="^(mine|all)$"),
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    List price alerts with pagination.

    Everyone gets their own alerts by default ("My alerts"). Staff can ask
    for every user's alerts with ``scope=all``: the Celery service user does
    this to find the active alerts to check. ``scope=all`` is ignored for
    regular users.

    Returns:
        - 200: Collection of price alerts with pagination meta
        - 403: Permission denied
    """
    logger.debug(
        f"Listing price alerts: limit={limit}, offset={offset}",
        extra={"action": "list_price_alerts", "user_id": current_user.id},
    )

    use_case = ListPriceAlertsUseCase(price_alert_repo)
    price_alerts, total = use_case.execute(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        user_id=None
        if scope == "all" and is_staff_or_superuser(current_user)
        else current_user.id,
    )
    return PriceAlertPresenter.handle_collection_success(price_alerts, total)


@router.get("/user/{user_id}", response_model=PriceAlertsCollectionResponse)
def get_price_alerts_by_user(
    user_id: int,
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get all price alerts for a specific user. Regular users can only access their own alerts; staff can access all.

    Returns:
        - 200: Collection of price alerts for the user
        - 403: Permission denied
    """
    logger.debug(
        f"Getting price alerts for user_id: {user_id}",
        extra={
            "action": "get_price_alerts_by_user",
            "target_user_id": user_id,
            "user_id": current_user.id,
        },
    )

    if not can_access_owned_resource(user_id, current_user):
        raise HTTPException(
            status_code=403,
            detail="You can only list your own price alerts.",
        )

    use_case = GetPriceAlertsByUserIdUseCase(price_alert_repo)
    price_alerts = use_case.execute(user_id)
    return PriceAlertPresenter.handle_collection_success(
        price_alerts, len(price_alerts)
    )


@router.get("/{price_alert_id}", response_model=PriceAlertReadResponse)
def get_price_alert(
    price_alert_id: int,
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get a single price alert by ID. Regular users can only access their own alerts; staff can access all.

    Returns:
        - 200: Price alert found
        - 403: Permission denied
        - 404: Price alert not found
    """
    logger.debug(
        f"Getting price alert ID: {price_alert_id}",
        extra={
            "action": "get_price_alert",
            "price_alert_id": price_alert_id,
            "user_id": current_user.id,
        },
    )

    use_case = GetPriceAlertByIdUseCase(price_alert_repo)
    price_alert = use_case.execute(price_alert_id)

    if not price_alert or not can_access_owned_resource(
        price_alert.user_id, current_user
    ):
        return PriceAlertPresenter.handle_not_found(f"id {price_alert_id}", "/data/id")

    return PriceAlertPresenter.handle_success(price_alert)


@router.get("/{price_alert_id}/products", response_model=ProductsCollectionResponse)
def get_products_by_price_alert(
    price_alert_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    filter_by_max_price: bool = Query(
        default=True,
        description="When true, only return products at or below the alert's max_price",
    ),
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    product_repo: ProductRepository = Depends(get_product_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get products matching a price alert's criteria, sorted by price ascending.

    Searches products whose title matches the alert's search_term and
    belong to one of the alert's source websites. By default, only
    products at or below the alert's max_price are returned.

    Returns:
        - 200: Collection of matching products with pagination meta
        - 403: Permission denied
        - 404: Price alert not found
    """
    logger.debug(
        f"Getting products for price alert ID: {price_alert_id}",
        extra={
            "action": "get_products_by_price_alert",
            "price_alert_id": price_alert_id,
            "user_id": current_user.id,
        },
    )

    owned = GetPriceAlertByIdUseCase(price_alert_repo).execute(price_alert_id)
    if not owned or not can_access_owned_resource(owned.user_id, current_user):
        return PriceAlertPresenter.handle_not_found(f"id {price_alert_id}", "/data/id")

    use_case = GetProductsByPriceAlertUseCase(price_alert_repo, product_repo)
    alert, products, total = use_case.execute(
        price_alert_id,
        limit=limit,
        offset=offset,
        filter_by_max_price=filter_by_max_price,
    )

    if not alert:
        return PriceAlertPresenter.handle_not_found(f"id {price_alert_id}", "/data/id")

    return ProductPresenter.handle_collection_success(products, total)


@router.get(
    "/{price_alert_id}/opportunities", response_model=ProductsCollectionResponse
)
def get_opportunities_by_price_alert(
    price_alert_id: int,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    product_repo: ProductRepository = Depends(get_product_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Get opportunity products for a price alert (always filtered by max_price).

    Returns products whose title matches the alert's search_term, belong to
    one of the alert's source websites, and are priced at or below max_price.

    Returns:
        - 200: Collection of opportunity products with pagination meta
        - 403: Permission denied
        - 404: Price alert not found
    """
    logger.debug(
        f"Getting opportunities for price alert ID: {price_alert_id}",
        extra={
            "action": "get_opportunities_by_price_alert",
            "price_alert_id": price_alert_id,
            "user_id": current_user.id,
        },
    )

    owned = GetPriceAlertByIdUseCase(price_alert_repo).execute(price_alert_id)
    if not owned or not can_access_owned_resource(owned.user_id, current_user):
        return PriceAlertPresenter.handle_not_found(f"id {price_alert_id}", "/data/id")

    use_case = GetProductsByPriceAlertUseCase(price_alert_repo, product_repo)
    alert, products, total = use_case.execute(
        price_alert_id,
        limit=limit,
        offset=offset,
        filter_by_max_price=True,
    )

    if not alert:
        return PriceAlertPresenter.handle_not_found(f"id {price_alert_id}", "/data/id")

    return ProductPresenter.handle_collection_success(products, total)


@router.put("/{price_alert_id}", response_model=PriceAlertReadResponse)
def update_price_alert(
    price_alert_id: int,
    price_alert_in: PriceAlertUpdateRequest,
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    price_alert_validator: PriceAlertValidator = Depends(get_price_alert_validator),
    plan_limits: PlanLimits = Depends(get_user_plan_limits),
    opportunities: NotifyAlertOpportunitiesUseCase = Depends(
        get_alert_opportunities_use_case
    ),
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Update an existing price alert. Regular users can only access their own alerts; staff can access all.

    If search_term or source_website_ids change, the linked SearchConfig is
    updated accordingly.  Deactivating an alert will deactivate its
    SearchConfig if no other active alert references it.

    Returns:
        - 200: Price alert updated successfully
        - 400: Validation errors (invalid type)
        - 403: Permission denied
        - 404: Price alert not found
        - 409: Duplicate search term for same user
        - 422: Invalid field values
    """
    logger.info(
        f"Updating price alert ID: {price_alert_id}",
        extra={
            "action": "update_price_alert",
            "price_alert_id": price_alert_id,
            "user_id": current_user.id,
        },
    )

    get_uc = GetPriceAlertByIdUseCase(price_alert_repo)
    existing = get_uc.execute(price_alert_id)

    if not existing or not can_access_owned_resource(existing.user_id, current_user):
        return PriceAlertPresenter.handle_not_found(f"id {price_alert_id}", "/data/id")

    validation_errors = price_alert_validator.validate_update_request(
        price_alert_id, price_alert_in
    )
    if validation_errors:
        logger.warning(
            f"Price alert update validation failed: {len(validation_errors)} errors",
            extra={
                "action": "price_alert_update_validation_failed",
                "price_alert_id": price_alert_id,
            },
        )
        return PriceAlertPresenter.handle_validation_errors(validation_errors)

    attrs = price_alert_in.data.attributes
    updated_entity = PriceAlertEntity(
        id=price_alert_id,
        search_term=attrs.search_term
        if attrs.search_term is not None
        else existing.search_term,
        max_price=attrs.max_price
        if attrs.max_price is not None
        else existing.max_price,
        is_active=attrs.is_active
        if attrs.is_active is not None
        else existing.is_active,
        frequency_minutes=attrs.frequency_minutes
        if attrs.frequency_minutes is not None
        else existing.frequency_minutes,
        last_triggered_at=existing.last_triggered_at,
        user_id=existing.user_id,
        search_config_id=existing.search_config_id,
        source_website_ids=attrs.source_website_ids
        if attrs.source_website_ids is not None
        else existing.source_website_ids,
        canonical_product_id=existing.canonical_product_id,
        condition=attrs.condition
        if existing.is_book_alert and attrs.condition is not None
        else existing.condition,
    )

    if not is_staff_or_superuser(current_user):
        limit_errors = [
            check_alert_limit(db, existing.user_id, plan_limits)
            if updated_entity.is_active and not existing.is_active
            else None,
            check_frequency_limit(updated_entity.frequency_minutes, plan_limits)
            if updated_entity.frequency_minutes != existing.frequency_minutes
            else None,
            check_source_limit(len(updated_entity.source_website_ids), plan_limits)
            if set(updated_entity.source_website_ids)
            != set(existing.source_website_ids)
            else None,
        ]
        limit_error = next((e for e in limit_errors if e), None)
        if limit_error:
            return PriceAlertPresenter.handle_validation_errors([limit_error])

    update_uc = UpdatePriceAlertUseCase(
        price_alert_repo, SearchConfigKeywordSearches(search_config_repo)
    )
    updated = update_uc.execute(price_alert_id, updated_entity)
    opportunities.execute(updated)

    logger.info(
        f"Price alert updated: '{updated.search_term}' (ID: {price_alert_id})",
        extra={
            "action": "price_alert_updated",
            "price_alert_id": price_alert_id,
            "user_id": current_user.id,
        },
    )
    return PriceAlertPresenter.handle_success(updated)


@router.delete("/{price_alert_id}", status_code=204)
def delete_price_alert(
    price_alert_id: int,
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    search_config_repo: SearchConfigRepository = Depends(get_search_config_repository),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """
    Delete a price alert. Regular users can only access their own alerts; staff can access all.

    If the associated SearchConfig is no longer used by any other active
    alert, it will be deactivated automatically.

    Returns:
        - 204: Deleted successfully (no content)
        - 403: Permission denied
        - 404: Price alert not found
    """
    logger.warning(
        f"Deleting price alert ID: {price_alert_id}",
        extra={
            "action": "delete_price_alert",
            "price_alert_id": price_alert_id,
            "user_id": current_user.id,
        },
    )

    get_uc = GetPriceAlertByIdUseCase(price_alert_repo)
    price_alert = get_uc.execute(price_alert_id)

    if not price_alert or not can_access_owned_resource(
        price_alert.user_id, current_user
    ):
        return PriceAlertPresenter.handle_not_found(f"id {price_alert_id}", "/data/id")

    delete_uc = DeletePriceAlertUseCase(
        price_alert_repo, SearchConfigKeywordSearches(search_config_repo)
    )
    deleted = delete_uc.execute(price_alert_id)

    if not deleted:
        return PriceAlertPresenter.handle_not_found(f"id {price_alert_id}", "/data/id")

    logger.warning(
        f"Price alert deleted (ID: {price_alert_id})",
        extra={
            "action": "price_alert_deleted",
            "price_alert_id": price_alert_id,
            "user_id": current_user.id,
        },
    )
    return None


@router.post("/{price_alert_id}/notify", status_code=200)
def trigger_price_alert_notification(
    price_alert_id: int,
    price_alert_repo: PriceAlertRepository = Depends(get_price_alert_repository),
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
    source_website_repo: SourceWebsiteRepository = Depends(
        get_source_website_repository
    ),
    notification_log_repo: NotificationLogRepository = Depends(
        get_notification_log_repository
    ),
    email_service: EmailServiceInterface = Depends(get_email_service),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Trigger email notification for a price alert. Regular users can only access their own alerts; staff can access all.

    Searches for matching products below the alert's max_price and sends
    an email to the alert's owner with the best match.

    Rate limiting: max 1 email per alert per NOTIFICATION_RATE_LIMIT_MINUTES (default 60).

    Returns:
        - 200: Notification result (sent, skipped, or failed)
        - 403: Permission denied
        - 404: Price alert not found
    """
    logger.info(
        f"Triggering notification for price alert ID: {price_alert_id}",
        extra={
            "action": "trigger_notification",
            "price_alert_id": price_alert_id,
            "user_id": current_user.id,
        },
    )

    use_case = SendPriceAlertNotificationUseCase(
        price_alert_repo=price_alert_repo,
        product_repo=CatalogListings(db),
        user_repo=UserAccountOwners(user_repo),
        source_website_repo=SourceWebsiteStores(source_website_repo),
        notification_log_repo=notification_log_repo,
        email_service=EmailServiceMailer(email_service),
    )
    logs, error = use_case.execute(price_alert_id)

    if error and not logs:
        if "not found" in error.lower():
            return JSONResponse(
                status_code=404,
                content=JsonApiErrorResponse(
                    errors=[
                        JsonApiError(
                            status="404",
                            code="NOT_FOUND",
                            title="Price alert not found",
                            detail=error,
                            source={"pointer": "/data/id"},
                        )
                    ]
                ).model_dump(),
                media_type="application/vnd.api+json",
            )
        return {
            "data": {
                "type": "notification_results",
                "attributes": {
                    "status": "skipped",
                    "message": error,
                    "notifications_sent": 0,
                },
            }
        }

    sent_count = sum(1 for log in logs if log.status == "sent")
    return {
        "data": {
            "type": "notification_results",
            "attributes": {
                "status": "sent" if sent_count > 0 else "failed",
                "message": error if error else f"{sent_count} notification(s) sent",
                "notifications_sent": sent_count,
            },
        }
    }
