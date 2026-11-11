"""GET /me/alerts: the logged-in user's product alerts (Phase 5 user area).

Each alert comes with its product today (lowest price in the alert's
condition, the store, the price verdict) and the e-mails already sent.
This module is the composition root for that read.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.app.alerts.entities import MyAlert
from src.app.alerts.persistence.product_snapshots import CatalogProductSnapshots
from src.app.alerts.persistence.repositories import (
    NotificationLogRepository,
    PriceAlertRepository,
)
from src.app.alerts.use_cases import ListMyAlertsUseCase
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database_config import get_db
from src.app.security.auth import get_current_active_user

router = APIRouter(tags=["me"], prefix="/me")


def get_my_alerts_use_case(db=Depends(get_db)) -> ListMyAlertsUseCase:
    return ListMyAlertsUseCase(
        PriceAlertRepository(db),
        CatalogProductSnapshots(db),
        NotificationLogRepository(db),
    )


def _iso(moment) -> str | None:
    return moment.isoformat() if moment else None


def _resource(item: MyAlert) -> dict:
    alert, product = item.alert, item.product
    best = product.lowest_for(alert.condition) if product else None
    verdict = product.verdicts.get(best[0]) if product and best else None
    return {
        "type": "my_alerts",
        "id": str(alert.id),
        "attributes": {
            "condition": alert.condition or "any",
            "max_price": alert.max_price,
            "is_active": alert.is_active,
            "created_at": _iso(alert.created_at),
            "product": None
            if product is None
            else {
                "id": product.id,
                "category": product.category,
                "title": product.title,
                "isbn13": product.isbn13,
                "cover_url": product.cover_url,
            },
            "today": None
            if best is None
            else {
                "condition": best[0],
                "price": best[1].price,
                "store": best[1].store,
                "verdict": verdict,
            },
            "notices": {
                "total": item.notices.total,
                "recent": [
                    {"sent_at": _iso(n.sent_at), "store": n.store}
                    for n in item.notices.recent
                ],
            },
        },
    }


@router.get("/alerts")
def my_alerts(
    use_case: ListMyAlertsUseCase = Depends(get_my_alerts_use_case),
    current_user: UserEntity = Depends(get_current_active_user),
):
    """The logged-in user's product alerts, active first (keyword alerts left out)."""
    items = use_case.execute(current_user.id)
    return JSONResponse(
        content={"data": [_resource(i) for i in items], "meta": {"total": len(items)}},
        media_type="application/vnd.api+json",
    )
