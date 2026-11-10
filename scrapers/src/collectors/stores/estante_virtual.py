"""Estante Virtual by ISBN: the cheapest new and the cheapest used offer.

Two plain HTTP requests per book, no browser:

1. ``/busca?q=<isbn>`` lists book groups; the one whose ``isbn`` attribute is
   the ISBN asked for is the book (Estante Virtual groups offers by ISBN).
2. The book page's ``window.__INITIAL_STATE__`` has, per condition, the
   cheapest offer (``groupProducts``). It does not say how many sellers
   there are: ``filters[].count`` is always 1.

Each condition gets its own URL (``?condition=novo|usado``, the page's own
tabs), so the backend keeps them as two offers.
"""

import json
from typing import Any

from src.collectors.offers import CollectedOffer
from src.collectors.ports import OfferSource, PageFetcher, StoreBlockedError

BASE_URL = "https://www.estantevirtual.com.br"
CONDITIONS = {"novo": "new", "usado": "used"}
_STATE_MARK = "window.__INITIAL_STATE__"


class EstanteVirtualSource(OfferSource):
    store_name = "estante_virtual"

    def __init__(self, fetcher: PageFetcher):
        self.fetcher = fetcher

    def find_offers(self, isbn13: str) -> list[CollectedOffer]:
        slug = parse_search(self.fetcher.get(f"{BASE_URL}/busca?q={isbn13}"), isbn13)
        if slug is None:
            return []
        page_url = f"{BASE_URL}{slug}"
        return parse_book(self.fetcher.get(page_url), isbn13, page_url)


def parse_search(html: str, isbn13: str) -> str | None:
    """The book page path (``/livro/...``) for this ISBN, or None."""
    state = _initial_state(html, "search page")
    for group in _find_lists(state, "parentSkus"):
        if isbn13 in _attributes(group).values() and group.get("productSlug"):
            return group["productSlug"]
    return None


def parse_book(html: str, isbn13: str, page_url: str) -> list[CollectedOffer]:
    """The cheapest new and used offers on a book page, for this ISBN only."""
    state = _initial_state(html, "book page")
    grouper = state.get("Product", {}).get("grouper", {})
    offers = []
    for label, condition in CONDITIONS.items():
        item = grouper.get("groupProducts", {}).get(label)
        if not item or _attributes(item).get("isbn") != isbn13:
            continue
        cents = _price_in_cents(item)
        if cents <= 0:
            continue
        offers.append(
            CollectedOffer(
                isbn=isbn13,
                url=f"{page_url}?condition={label}",
                price=cents / 100,
                condition=condition,
                is_available=bool(item.get("available", True)),
                city=item.get("city") or None,
            )
        )
    return offers


def _price_in_cents(item: dict[str, Any]) -> int:
    """The price the page shows: the offer's sale price, which includes
    promotions (``prices[0].salePrice``). The item's own ``salePrice`` is the
    full price, before them."""
    prices = item.get("prices") or []
    if prices and prices[0].get("salePrice"):
        return int(prices[0]["salePrice"])
    return int(item.get("salePrice") or 0)


def _initial_state(html: str, what: str) -> dict[str, Any]:
    """The page's state JSON. A page without it is not the page we asked for
    (a challenge or an error page), which counts as a block."""
    start = html.find(_STATE_MARK)
    if start == -1:
        raise StoreBlockedError(f"unexpected {what}: no state")
    start = html.find("{", start)
    try:
        state, _ = json.JSONDecoder().raw_decode(html, start)
    except (ValueError, IndexError) as e:
        raise StoreBlockedError(f"unexpected {what}: bad state") from e
    return state


def _attributes(item: dict[str, Any]) -> dict[str, Any]:
    return {a.get("name"): a.get("value") for a in item.get("attributes", [])}


def _find_lists(node: Any, key: str):
    """Every item of every list stored under ``key``, anywhere in ``node``."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, list):
                yield from v
            else:
                yield from _find_lists(v, key)
    elif isinstance(node, list):
        for v in node:
            yield from _find_lists(v, key)
