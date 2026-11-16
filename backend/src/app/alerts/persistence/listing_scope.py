"""Catalog's ListingScope over alerts' tables: listings an alert found."""

from sqlalchemy import ColumnElement, and_, exists

from src.app.alerts.persistence.models import PriceAlert as PriceAlertModel
from src.app.alerts.persistence.models import price_alert_source_website
from src.app.catalog.persistence.models import Product as ProductModel
from src.app.catalog.ports import ListingScope
from src.app.infrastructure.database.text_match import title_contains


class AlertListingScope(ListingScope):
    def found_by_alerts(
        self,
        *,
        user_id: int | None = None,
        alert_id: int | None = None,
        current_price: ColumnElement | None = None,
    ) -> ColumnElement[bool]:
        matches = [
            PriceAlertModel.deleted_at.is_(None),
            price_alert_source_website.c.price_alert_id == PriceAlertModel.id,
            price_alert_source_website.c.source_website_id
            == ProductModel.source_website_id,
            title_contains(ProductModel.title, PriceAlertModel.search_term),
        ]
        if user_id is not None:
            matches.append(PriceAlertModel.user_id == user_id)
        if alert_id is not None:
            matches.append(PriceAlertModel.id == alert_id)
        if current_price is not None:
            matches.append(current_price <= PriceAlertModel.max_price)
        return (
            exists()
            .where(and_(*matches))
            .correlate_except(PriceAlertModel, price_alert_source_website)
        )
