from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.app.alerts.persistence.models import (
    PriceAlert,
    price_alert_source_website,
)
from src.app.catalog.persistence.models import (
    PriceHistory,
    Product,
)
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database.models.search_execution_log_model import (
    SearchExecutionLog,
)
from src.app.infrastructure.database.text_match import title_contains
from src.app.infrastructure.database_config import get_db
from src.app.security.auth import get_current_active_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    opportunities_limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_active_user),
):
    user_id = current_user.id

    # Alert counts (exclude soft-deleted)
    total_alerts = (
        db.query(func.count(PriceAlert.id))
        .filter(
            PriceAlert.user_id == user_id,
            PriceAlert.deleted_at.is_(None),
        )
        .scalar()
    )
    active_alerts = (
        db.query(func.count(PriceAlert.id))
        .filter(
            PriceAlert.user_id == user_id,
            PriceAlert.is_active.is_(True),
            PriceAlert.deleted_at.is_(None),
        )
        .scalar()
    )

    # Fetch active alerts with source websites eagerly loaded
    active_alert_models = (
        db.query(PriceAlert)
        .options(joinedload(PriceAlert.source_websites))
        .filter(
            PriceAlert.user_id == user_id,
            PriceAlert.is_active.is_(True),
            PriceAlert.deleted_at.is_(None),
        )
        .all()
    )

    # Recent opportunities: products matching active alerts within max_price
    # Build a subquery for latest price per product
    latest_price_sq = (
        db.query(
            PriceHistory.product_id,
            func.max(PriceHistory.id).label("max_id"),
        )
        .group_by(PriceHistory.product_id)
        .subquery()
    )

    price_sq = (
        db.query(
            PriceHistory.product_id,
            PriceHistory.price.label("latest_price"),
        )
        .join(
            latest_price_sq,
            (PriceHistory.product_id == latest_price_sq.c.product_id)
            & (PriceHistory.id == latest_price_sq.c.max_id),
        )
        .subquery()
    )

    opportunities = []
    for alert in active_alert_models:
        sw_ids = [sw.id for sw in alert.source_websites]
        if not sw_ids:
            continue

        rows = (
            db.query(Product, price_sq.c.latest_price)
            .join(price_sq, Product.id == price_sq.c.product_id)
            .join(
                price_alert_source_website,
                price_alert_source_website.c.source_website_id
                == Product.source_website_id,
            )
            .filter(
                price_alert_source_website.c.price_alert_id == alert.id,
                title_contains(Product.title, alert.search_term),
                price_sq.c.latest_price.isnot(None),
                price_sq.c.latest_price <= alert.max_price,
                Product.is_available.is_(True),
            )
            .order_by(price_sq.c.latest_price.asc())
            .limit(5)
            .all()
        )

        for p, latest_price in rows:
            opportunities.append(
                {
                    "id": str(p.id),
                    "title": p.title,
                    "url": p.url,
                    "current-price": float(latest_price),
                    "alert-max-price": float(alert.max_price),
                    "alert-search-term": alert.search_term,
                    "alert-id": str(alert.id),
                    "source-website-id": p.source_website_id,
                    "created-at": p.created_at.isoformat() if p.created_at else None,
                }
            )

    # Sort by most recent and limit
    opportunities.sort(key=lambda o: o.get("created-at") or "", reverse=True)
    opportunities = opportunities[:opportunities_limit]

    # Next checks: compute from last execution per search_config
    unique_config_ids = list(
        {a.search_config_id for a in active_alert_models if a.search_config_id}
    )

    # Fetch latest execution per search_config in one query
    last_executions = {}
    if unique_config_ids:
        latest_subq = (
            db.query(
                SearchExecutionLog.search_config_id,
                func.max(SearchExecutionLog.started_at).label("last_started"),
            )
            .filter(SearchExecutionLog.search_config_id.in_(unique_config_ids))
            .group_by(SearchExecutionLog.search_config_id)
            .all()
        )
        last_executions = {row[0]: row[1] for row in latest_subq}

    next_checks = []
    for alert in active_alert_models:
        last_run = last_executions.get(alert.search_config_id)
        next_check_at = None
        if last_run:
            next_check_at = (
                last_run + timedelta(minutes=alert.frequency_minutes)
            ).isoformat()

        next_checks.append(
            {
                "alert-id": str(alert.id),
                "search-term": alert.search_term,
                "frequency-minutes": alert.frequency_minutes,
                "last-triggered-at": last_run.isoformat() if last_run else None,
                "next-check-at": next_check_at,
            }
        )

    # Sort by nearest check first
    next_checks.sort(key=lambda c: c.get("next-check-at") or "9999")

    return {
        "data": {
            "type": "dashboard-summary",
            "id": str(user_id),
            "attributes": {
                "active-alerts": active_alerts,
                "total-alerts": total_alerts,
                "recent-opportunities": opportunities,
                "next-checks": next_checks,
            },
        }
    }
