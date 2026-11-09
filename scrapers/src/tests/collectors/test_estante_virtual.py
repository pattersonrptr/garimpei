"""Estante Virtual parsing, on pages shaped like the real ones (Nov 2026)."""

import pytest

from src.collectors.ports import StoreBlockedError
from src.collectors.stores.estante_virtual import (
    BASE_URL,
    EstanteVirtualSource,
    parse_book,
    parse_search,
)
from src.tests.collectors.fakes import PagesByUrl, page_with_state

ISBN = "9788535914849"
SLUG = "/livro/1984-017-4778-000-BK"
PAGE = f"{BASE_URL}{SLUG}"


def attrs(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def search_page(*groups):
    return page_with_state({"SearchPage": {"results": {"parentSkus": list(groups)}}})


def group(isbn, slug):
    return {"productSlug": slug, "attributes": attrs(isbn=isbn, group_by=isbn)}


def book_page(novo=2000, usado=1750, novo_isbn=ISBN, usado_offer_price=None):
    products = {}
    if novo is not None:
        products["novo"] = {
            "salePrice": novo,
            "prices": [{"salePrice": novo}],
            "available": True,
            "city": "",
            "attributes": attrs(isbn=novo_isbn, condition="novo"),
        }
    if usado is not None:
        products["usado"] = {
            "salePrice": usado,
            "prices": [{"salePrice": usado_offer_price or usado}],
            "available": True,
            "city": "",
            "attributes": attrs(isbn=ISBN, condition="usado"),
        }
    return page_with_state(
        {
            "Product": {
                "grouper": {
                    "groupProducts": products,
                }
            }
        }
    )


class TestParseSearch:
    def test_picks_the_group_with_the_exact_isbn(self):
        html = search_page(
            group("9788535900000", "/livro/1984-outra-edicao"), group(ISBN, SLUG)
        )

        assert parse_search(html, ISBN) == SLUG

    def test_no_group_with_that_isbn_means_not_found(self):
        html = search_page(group("9788535900000", "/livro/outro"))

        assert parse_search(html, ISBN) is None

    def test_a_page_without_state_is_a_block(self):
        with pytest.raises(StoreBlockedError):
            parse_search("<html>Verifique que você não é um robô</html>", ISBN)


class TestParseBook:
    def test_cheapest_new_and_used_as_two_offers(self):
        offers = parse_book(book_page(), ISBN, PAGE)

        by_condition = {o.condition: o for o in offers}
        assert by_condition["new"].price == 20.0
        assert by_condition["new"].url == f"{PAGE}?condition=novo"
        assert by_condition["used"].price == 17.5
        assert by_condition["used"].url == f"{PAGE}?condition=usado"
        assert all(o.isbn == ISBN and o.city is None for o in offers)

    def test_the_price_shown_includes_promotions(self):
        # Real case (Nov 2026): item salePrice 10990, offer salePrice 9341
        # under a "PayDay" promotion; the page shows R$ 93,41.
        offers = parse_book(
            book_page(novo=None, usado=10990, usado_offer_price=9341), ISBN, PAGE
        )

        assert offers[0].price == 93.41

    def test_only_used_copies(self):
        offers = parse_book(book_page(novo=None), ISBN, PAGE)

        assert [o.condition for o in offers] == ["used"]

    def test_an_offer_for_another_isbn_is_ignored(self):
        offers = parse_book(book_page(novo_isbn="9780000000002"), ISBN, PAGE)

        assert [o.condition for o in offers] == ["used"]

    def test_a_zero_price_is_ignored(self):
        assert parse_book(book_page(novo=0, usado=None), ISBN, PAGE) == []

    def test_broken_state_is_a_block(self):
        with pytest.raises(StoreBlockedError):
            parse_book("<script>window.__INITIAL_STATE__ = {oops</script>", ISBN, PAGE)


class TestFindOffers:
    def test_search_then_book_page(self):
        fetcher = PagesByUrl(
            {
                f"{BASE_URL}/busca?q={ISBN}": search_page(group(ISBN, SLUG)),
                PAGE: book_page(),
            }
        )

        offers = EstanteVirtualSource(fetcher).find_offers(ISBN)

        assert len(offers) == 2
        assert fetcher.calls == [f"{BASE_URL}/busca?q={ISBN}", PAGE]

    def test_not_found_stops_after_the_search(self):
        fetcher = PagesByUrl({f"{BASE_URL}/busca?q={ISBN}": search_page()})

        assert EstanteVirtualSource(fetcher).find_offers(ISBN) == []
        assert len(fetcher.calls) == 1
