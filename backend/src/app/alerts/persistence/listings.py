"""Listings over the catalog's offers (alerts' Listings port)."""

from sqlalchemy.orm import Session

from src.app.alerts.entities import Listing
from src.app.alerts.ports import Listings
from src.app.catalog.entities import Product, ProductListFilters
from src.app.catalog.persistence.repositories import ProductRepository


class CatalogListings(Listings):
    def __init__(self, db: Session):
        self.products = ProductRepository(db)

    def get_by_id(self, listing_id: int) -> Listing | None:
        product = self.products.get_by_id(listing_id)
        return _listing(product) if product else None

    def cheapest_match(
        self, search_term: str, store_ids: list[int], max_price: float
    ) -> Listing | None:
        products, _ = self.products.search_by_term_and_sources(
            search_term=search_term,
            source_website_ids=store_ids,
            max_price=max_price,
            limit=1,
            offset=0,
        )
        return _listing(products[0]) if products else None

    def opportunities_for_alert(self, alert_id: int, limit: int) -> list[Listing]:
        return self._listings(
            limit,
            ProductListFilters(matching_alert_id=alert_id, opportunities_only=True),
        )

    def available_offers_for_book(
        self, canonical_product_id: int, limit: int
    ) -> list[Listing]:
        return self._listings(
            limit,
            ProductListFilters(
                canonical_product_id=canonical_product_id, is_available=True
            ),
        )

    def _listings(self, limit: int, filters: ProductListFilters) -> list[Listing]:
        products, _ = self.products.get_all(limit=limit, filters=filters)
        return [_listing(product) for product in products]


def _listing(product: Product) -> Listing:
    assert product.id is not None  # saved products always have an id
    return Listing(
        id=product.id,
        title=product.title,
        url=product.url,
        store_id=product.source_website_id,
        price=product.current_price,
        condition=product.condition.value,
        is_available=product.is_available,
    )
