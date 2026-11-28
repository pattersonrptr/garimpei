from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import get_current_superuser
from src.app.admin import wiring
from src.app.admin.http.presenter import present_cleanup, present_summary
from src.app.catalog import wiring as catalog_wiring
from src.app.catalog.http.listing_scope import get_listing_scope
from src.app.catalog.ports import ListingScope
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
    scope: ListingScope = Depends(get_listing_scope),
    current_user: UserEntity = Depends(get_current_superuser),
):
    """Delete products not updated for `days_old` days that no active alert
    finds (its search term in the title, the product's store among the
    alert's). With `dry_run`, only count them."""
    result = catalog_wiring.delete_stale_products(db, scope).execute(
        days_old=days_old, dry_run=dry_run
    )
    return present_cleanup(result, dry_run=dry_run)
