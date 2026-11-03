from fastapi import APIRouter, Depends, Query

from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.notification_log_repository import (
    NotificationLogRepository,
)
from src.app.infrastructure.repositories.price_alert_repository import (
    PriceAlertRepository,
)
from src.app.infrastructure.repositories.product_repository import ProductRepository
from src.app.infrastructure.repositories.source_website_repository import (
    SourceWebsiteRepository,
)
from src.app.infrastructure.repositories.user_repository import UserRepository
from src.app.interfaces.http.presenters.notification_log_presenter import (
    NotificationLogPresenter,
)
from src.app.interfaces.http.schemas.notification_log_schema import (
    NotificationLogReadResponse,
    NotificationLogsCollectionResponse,
)
from src.app.security.auth import get_current_staff_user
from src.app.use_cases.notification_log_use_cases import (
    DeleteNotificationLogUseCase,
    GetNotificationLogByIdUseCase,
    GetNotificationLogsByPriceAlertIdUseCase,
    ListNotificationLogsUseCase,
)
from src.config.logging_config import get_logger

router = APIRouter(tags=["notification_logs"], prefix="/notification-logs")

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


def get_notification_log_repository(
    db=Depends(get_db),
) -> NotificationLogRepository:
    """Dependency injection for NotificationLogRepository."""
    return NotificationLogRepository(db)


def get_price_alert_repository(db=Depends(get_db)) -> PriceAlertRepository:
    return PriceAlertRepository(db)


def get_product_repository(db=Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)


def get_user_repository(db=Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_source_website_repository(db=Depends(get_db)) -> SourceWebsiteRepository:
    return SourceWebsiteRepository(db)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/", response_model=NotificationLogsCollectionResponse)
def list_notification_logs(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = Query(default=None),
    sort_order: str | None = Query(default="desc", pattern="^(asc|desc)$"),
    notification_log_repo: NotificationLogRepository = Depends(
        get_notification_log_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    List all notification logs with pagination. Requires staff or superuser access.

    Returns:
        - 200: Collection of notification logs with pagination meta
        - 403: Permission denied
    """
    logger.debug(
        f"Listing notification logs: limit={limit}, offset={offset}",
        extra={"action": "list_notification_logs", "user_id": current_user.id},
    )

    use_case = ListNotificationLogsUseCase(notification_log_repo)
    logs, total = use_case.execute(
        limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
    )
    return NotificationLogPresenter.handle_collection_success(logs, total)


@router.get(
    "/price-alert/{price_alert_id}",
    response_model=NotificationLogsCollectionResponse,
)
def get_notification_logs_by_price_alert(
    price_alert_id: int,
    notification_log_repo: NotificationLogRepository = Depends(
        get_notification_log_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Get all notification logs for a specific price alert.
    Requires staff or superuser access.

    Returns:
        - 200: Collection of notification logs for the alert
        - 403: Permission denied
    """
    logger.debug(
        f"Getting notification logs for price_alert_id: {price_alert_id}",
        extra={
            "action": "get_notification_logs_by_alert",
            "price_alert_id": price_alert_id,
            "user_id": current_user.id,
        },
    )

    use_case = GetNotificationLogsByPriceAlertIdUseCase(notification_log_repo)
    logs = use_case.execute(price_alert_id)
    return NotificationLogPresenter.handle_collection_success(logs, len(logs))


@router.get("/{notification_log_id}", response_model=NotificationLogReadResponse)
def get_notification_log(
    notification_log_id: int,
    notification_log_repo: NotificationLogRepository = Depends(
        get_notification_log_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Get a single notification log by ID. Requires staff or superuser access.

    Returns:
        - 200: Notification log found
        - 403: Permission denied
        - 404: Notification log not found
    """
    logger.debug(
        f"Getting notification log ID: {notification_log_id}",
        extra={
            "action": "get_notification_log",
            "notification_log_id": notification_log_id,
            "user_id": current_user.id,
        },
    )

    use_case = GetNotificationLogByIdUseCase(notification_log_repo)
    log = use_case.execute(notification_log_id)

    if not log:
        return NotificationLogPresenter.handle_not_found(
            f"id {notification_log_id}", "/data/id"
        )

    return NotificationLogPresenter.handle_success(log)


@router.delete("/{notification_log_id}", status_code=204)
def delete_notification_log(
    notification_log_id: int,
    notification_log_repo: NotificationLogRepository = Depends(
        get_notification_log_repository
    ),
    current_user: UserEntity = Depends(get_current_staff_user),
):
    """
    Delete a notification log. Requires staff or superuser access.

    Returns:
        - 204: Deleted successfully
        - 403: Permission denied
        - 404: Notification log not found
    """
    logger.warning(
        f"Deleting notification log ID: {notification_log_id}",
        extra={
            "action": "delete_notification_log",
            "notification_log_id": notification_log_id,
            "user_id": current_user.id,
        },
    )

    use_case = DeleteNotificationLogUseCase(notification_log_repo)
    deleted = use_case.execute(notification_log_id)

    if not deleted:
        return NotificationLogPresenter.handle_not_found(
            f"id {notification_log_id}", "/data/id"
        )

    return None
