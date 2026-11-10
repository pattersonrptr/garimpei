"""Stores built on VTEX, through its public catalog API (JSON, no HTML).

``/api/catalog_system/pub/products/search?fq=alternateIds_Ean:<ean>`` returns
the products with that EAN. For books the EAN is the ISBN-13; for most other
products it is the barcode, so the same adapter serves any category.

Bookstores sell new books, so every offer here is ``new``. When a product has
several sellers, the cheapest one with stock wins; with no stock anywhere, the
store's own seller is reported as unavailable.
"""

import json
from typing import Any

from src.collectors.offers import CollectedOffer
from src.collectors.ports import OfferSource, PageFetcher, StoreBlockedError

SEARCH_PATH = "/api/catalog_system/pub/products/search?fq=alternateIds_Ean:{ean}"


class VtexSource(OfferSource):
    def __init__(self, fetcher: PageFetcher, *, store_name: str, base_url: str):
        self.fetcher = fetcher
        self.store_name = store_name
        self.base_url = base_url.rstrip("/")

    def find_offers(self, isbn13: str) -> list[CollectedOffer]:
        body = self.fetcher.get(self.base_url + SEARCH_PATH.format(ean=isbn13))
        return parse_products(body, isbn13)


def parse_products(body: str, ean: str) -> list[CollectedOffer]:
    """One offer per product that has an item with this EAN."""
    try:
        products = json.loads(body)
    except ValueError as e:
        # Not JSON: a challenge or an error page, which counts as a block.
        raise StoreBlockedError("unexpected answer: not JSON") from e
    if not isinstance(products, list):
        raise StoreBlockedError("unexpected answer: not a product list")

    offers = []
    for product in products:
        link = product.get("link")
        items = [i for i in product.get("items", []) if i.get("ean") == ean]
        best = _best_offer(items)
        if link and best:
            price, available = best
            offers.append(
                CollectedOffer(
                    isbn=ean,
                    url=link,
                    price=price,
                    condition="new",
                    is_available=available,
                )
            )
    return offers


def _best_offer(items: list[dict[str, Any]]) -> tuple[float, bool] | None:
    """(price, available): the cheapest seller with stock, else the default
    seller's price marked unavailable, else None."""
    in_stock, default = [], None
    for item in items:
        for seller in item.get("sellers", []):
            offer = seller.get("commertialOffer") or {}  # sic, VTEX's spelling
            price = offer.get("Price") or 0
            if price <= 0:
                continue
            if offer.get("IsAvailable") and offer.get("AvailableQuantity", 0) > 0:
                in_stock.append(price)
            elif seller.get("sellerDefault") and default is None:
                default = price
    if in_stock:
        return min(in_stock), True
    if default is not None:
        return default, False
    return None
