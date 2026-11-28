from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import not_
from sqlalchemy.orm import Session

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import get_current_superuser
from src.app.admin import wiring
from src.app.admin.http.presenter import present_summary
from src.app.alerts.persistence.models import (
    PriceAlert,
    price_alert_source_website,
)
from src.app.catalog.persistence.models import Product
from src.app.infrastructure.database.text_match import title_contains
from src.app.infrastructure.database_config import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/summary")
def get_admin_summary(
    db: Session = Depends(get_db),
    current_user: UserEntity = Depends(get_current_superuser),
):
    return present_summary(wiring.admin_summary(db).execute())


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
