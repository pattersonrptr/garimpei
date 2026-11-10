"""VTEX catalog API parsing, on answers shaped like the real ones (Nov 2026,
Livraria da Vila and Martins Fontes)."""

import json

import pytest

from src.collectors.ports import StoreBlockedError
from src.collectors.stores.vtex import SEARCH_PATH, VtexSource, parse_products
from src.tests.collectors.fakes import PagesByUrl

ISBN = "9788535914849"
LINK = (
    "https://www.livrariadavila.com.br/58926-1984---traducao-de-alexandre-hubner-e-h/p"
)


def seller(price, available=True, quantity=99999, default=True):
    return {
        "sellerName": "Livraria",
        "sellerDefault": default,
        "commertialOffer": {
            "Price": price,
            "ListPrice": price,
            "IsAvailable": available,
            "AvailableQuantity": quantity,
        },
    }


def product(*sellers, ean=ISBN, link=LINK):
    return {
        "productName": "1984 - Tradução de Alexandre Hubner e Heloisa Jahn",
        "link": link,
        "items": [{"ean": ean, "sellers": list(sellers)}],
    }


def answer(*products):
    return json.dumps(list(products))


def test_a_book_in_stock_is_one_new_offer():
    offers = parse_products(answer(product(seller(59.9))), ISBN)

    assert len(offers) == 1
    assert offers[0].url == LINK
    assert offers[0].price == 59.9
    assert offers[0].condition == "new"
    assert offers[0].is_available is True


def test_the_cheapest_seller_with_stock_wins():
    sellers = [seller(59.9), seller(49.9, default=False), seller(39.9, quantity=0)]

    offers = parse_products(answer(product(*sellers)), ISBN)

    assert offers[0].price == 49.9


def test_out_of_stock_everywhere_is_reported_unavailable():
    offers = parse_products(answer(product(seller(59.9, available=False))), ISBN)

    assert offers[0].price == 59.9
    assert offers[0].is_available is False


def test_items_with_another_ean_are_ignored():
    assert (
        parse_products(answer(product(seller(10.0), ean="9780000000002")), ISBN) == []
    )


def test_no_product_means_not_found():
    assert parse_products("[]", ISBN) == []


@pytest.mark.parametrize("body", ["<html>challenge</html>", '{"error": "x"}'])
def test_an_answer_that_is_not_a_product_list_is_a_block(body):
    with pytest.raises(StoreBlockedError):
        parse_products(body, ISBN)


def test_asks_the_store_api_by_ean():
    base = "https://www.martinsfontespaulista.com.br"
    url = base + SEARCH_PATH.format(ean=ISBN)
    fetcher = PagesByUrl({url: answer(product(seller(59.9)))})

    source = VtexSource(fetcher, store_name="Martins Fontes", base_url=base + "/")
    offers = source.find_offers(ISBN)

    assert fetcher.calls == [url]
    assert source.store_name == "Martins Fontes"
    assert len(offers) == 1
