from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, not_
from sqlalchemy.orm import Session

from src.app.catalog.persistence.models import Product
from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database.models.price_alert_model import PriceAlert
from src.app.infrastructure.database.models.price_alert_source_website_model import (
    price_alert_source_website,
)
from src.app.infrastructure.database.models.search_execution_log_model import (
    SearchExecutionLog,
)
from src.app.infrastructure.database.models.source_website_model import SourceWebsite
from src.app.infrastructure.database.models.user_model import User
from src.app.infrastructure.database.text_match import title_contains
from src.app.infrastructure.database_config import get_db
from src.app.security.auth import get_current_superuser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/summary")
def get_admin_summary(
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_superuser),
):
    total_users = db.query(func.count(User.id)).scalar()
    active_users = (
        db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar()
    )

    total_products = db.query(func.count(Product.id)).scalar()
    total_alerts = (
        db.query(func.count(PriceAlert.id))
        .filter(PriceAlert.deleted_at.is_(None))
        .scalar()
    )
    active_alerts = (
        db.query(func.count(PriceAlert.id))
        .filter(
            PriceAlert.is_active.is_(True),
            PriceAlert.deleted_at.is_(None),
        )
        .scalar()
    )

    total_source_websites = db.query(func.count(SourceWebsite.id)).scalar()
    active_source_websites = (
        db.query(func.count(SourceWebsite.id))
        .filter(SourceWebsite.is_active.is_(True))
        .scalar()
    )

    recent_executions = (
        db.query(SearchExecutionLog)
        .order_by(SearchExecutionLog.started_at.desc())
        .limit(20)
        .all()
    )

    success_count = sum(1 for e in recent_executions if e.status == "success")
    failed_count = sum(1 for e in recent_executions if e.status == "failed")

    return {
        "data": {
            "type": "admin-summary",
            "id": "1",
            "attributes": {
                "total-users": total_users,
                "active-users": active_users,
                "total-products": total_products,
                "total-alerts": total_alerts,
                "active-alerts": active_alerts,
                "total-source-websites": total_source_websites,
                "active-source-websites": active_source_websites,
                "recent-executions": [
                    {
                        "id": e.id,
                        "search-config-id": e.search_config_id,
                        "status": e.status,
                        "results-count": e.results_count,
                        "error-message": e.error_message,
                        "started-at": e.started_at.isoformat()
                        if e.started_at
                        else None,
                        "finished-at": e.finished_at.isoformat()
                        if e.finished_at
                        else None,
                    }
                    for e in recent_executions
                ],
                "scraper-stats": {
                    "recent-total": len(recent_executions),
                    "success-count": success_count,
                    "failed-count": failed_count,
                },
            },
        }
    }


@router.post("/cleanup-products")
def cleanup_orphaned_products(
    days_old: int = Query(default=30, ge=1, le=365),
    dry_run: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_superuser),
):
    """Delete products older than `days_old` days that don't match any active alert.

    A product is "orphaned" if no active, non-deleted price alert's search_term
    appears in the product title AND the product's source_website is in the
    alert's source_websites.

    Args:
        days_old: Minimum age in days for a product to be eligible for cleanup.
        dry_run: If True, return the count without deleting.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days_old)

    # Subquery: product IDs that match at least one active alert
    matched_product_ids = (
        db.query(Product.id)
        .join(
            price_alert_source_website,
            price_alert_source_website.c.source_website_id == Product.source_website_id,
        )
        .join(
            PriceAlert,
            PriceAlert.id == price_alert_source_website.c.price_alert_id,
        )
        .filter(
            PriceAlert.is_active.is_(True),
            PriceAlert.deleted_at.is_(None),
            title_contains(Product.title, PriceAlert.search_term),
        )
        .distinct()
        .subquery()
    )

    orphaned_query = db.query(Product).filter(
        Product.updated_at < cutoff,
        not_(Product.id.in_(db.query(matched_product_ids.c.id))),
    )

    count = orphaned_query.count()

    if dry_run:
        return {
            "data": {
                "type": "cleanup-result",
                "id": "1",
                "attributes": {
                    "dry-run": True,
                    "eligible-count": count,
                    "deleted-count": 0,
                },
            }
        }

    orphaned_query.delete(synchronize_session=False)
    db.commit()

    return {
        "data": {
            "type": "cleanup-result",
            "id": "1",
            "attributes": {
                "dry-run": False,
                "eligible-count": count,
                "deleted-count": count,
            },
        }
    }
