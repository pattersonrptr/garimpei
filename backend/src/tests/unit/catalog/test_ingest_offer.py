"""IngestOfferUseCase with in-memory doubles (no database, no network)."""

from datetime import UTC, datetime

import pytest

from src.app.catalog.entities import BookMetadata, ProductCondition
from src.app.catalog.entities import Product as ProductEntity
from src.app.catalog.isbn import InvalidIsbnError
from src.app.catalog.use_cases import (
    BookNotFoundError,
    GetOrCreateBookByIsbnUseCase,
    IngestOfferUseCase,
    InvalidOfferError,
    OfferInput,
)
from src.tests.unit.catalog.test_get_or_create_book import (
    FakeMetadata,
    InMemoryProducts,
)

ISBN13 = "9788535914849"
URL = "https://www.estantevirtual.com.br/livro/1984-usado-123"
CHECKED_AT = datetime(2026, 11, 10, 3, 0, tzinfo=UTC)


class InMemoryOffers:
    def __init__(self):
        self.by_id = {}

    def get_by_url(self, url):
        return next((o for o in self.by_id.values() if o.url == url), None)

    def create(self, offer):
        offer.id = len(self.by_id) + 1
        self.by_id[offer.id] = offer
        return offer

    def update(self, offer_id, offer):
        self.by_id[offer_id] = offer
        return offer


class InMemoryPrices:
    def __init__(self):
        self.points = []

    def create(self, point):
        point.created_at = CHECKED_AT  # the database's clock
        self.points.append(point)
        return point


@pytest.fixture
def world():
    book = BookMetadata(isbn13=ISBN13, title="1984", authors=("George Orwell",))
    metadata = FakeMetadata(book)
    offers, prices = InMemoryOffers(), InMemoryPrices()
    use_case = IngestOfferUseCase(
        get_book=GetOrCreateBookByIsbnUseCase(InMemoryProducts(), metadata),
        offers=offers,
        prices=prices,
    )
    return use_case, offers, prices, metadata


def an_offer(**changes):
    values = {
        "isbn": "978-85-359-1484-9",
        "source_website_id": 3,
        "url": URL,
        "price": 28.5,
        "condition": ProductCondition.USED,
        "city": "São Paulo",
        "state": "SP",
    }
    values.update(changes)
    return OfferInput(**values)


def test_a_new_offer_is_created_linked_to_its_book(world):
    use_case, offers, prices, _ = world

    result = use_case.execute(an_offer())

    assert result.created is True
    offer = offers.by_id[result.offer.id]
    assert offer.url == URL
    assert offer.title == "1984"  # from the book's metadata, not the store
    assert offer.condition == ProductCondition.USED
    assert offer.canonical_product_id == result.book.id
    assert offer.source_website_id == 3
    assert (offer.city, offer.state) == ("São Paulo", "SP")
    assert [(p.product_id, p.price) for p in prices.points] == [(offer.id, 28.5)]
    assert result.offer.current_price == 28.5
    assert result.offer.last_checked_at == CHECKED_AT  # "updated X h ago"


def test_the_same_url_updates_the_offer_and_adds_a_price_point(world):
    use_case, offers, prices, metadata = world
    first = use_case.execute(an_offer(price=28.5))

    second = use_case.execute(an_offer(price=26.0, is_available=False))

    assert second.created is False
    assert second.offer.id == first.offer.id
    assert len(offers.by_id) == 1
    assert offers.by_id[first.offer.id].is_available is False
    assert [p.price for p in prices.points] == [28.5, 26.0]
    assert metadata.calls == [ISBN13]  # the book was looked up only once


def test_new_and_used_offers_of_the_same_book_share_the_book(world):
    use_case, offers, _, _ = world

    used = use_case.execute(an_offer(url=URL, condition=ProductCondition.USED))
    new = use_case.execute(
        an_offer(url=URL + "-novo", condition=ProductCondition.NEW, price=54.9)
    )

    assert used.book.id == new.book.id
    assert len(offers.by_id) == 2


def test_an_existing_offer_from_a_keyword_search_gets_linked(world):
    use_case, offers, _, _ = world
    old = offers.create(
        ProductEntity(
            url=URL, title="1984 George Orwell usado bom estado", source_website_id=3
        )
    )
    assert old.canonical_product_id is None

    result = use_case.execute(an_offer())

    assert result.created is False
    assert offers.by_id[old.id].canonical_product_id == result.book.id


@pytest.mark.parametrize(
    "changes", [{"price": 0}, {"price": -1.0}, {"url": "   "}], ids=str
)
def test_invalid_offers_are_rejected_before_anything_is_stored(world, changes):
    use_case, offers, prices, metadata = world

    with pytest.raises(InvalidOfferError):
        use_case.execute(an_offer(**changes))

    assert offers.by_id == {}
    assert prices.points == []
    assert metadata.calls == []


def test_an_invalid_isbn_stores_nothing(world):
    use_case, offers, prices, _ = world

    with pytest.raises(InvalidIsbnError):
        use_case.execute(an_offer(isbn="123"))

    assert offers.by_id == {}
    assert prices.points == []


def test_an_unknown_book_stores_nothing():
    offers, prices = InMemoryOffers(), InMemoryPrices()
    use_case = IngestOfferUseCase(
        get_book=GetOrCreateBookByIsbnUseCase(InMemoryProducts(), FakeMetadata(None)),
        offers=offers,
        prices=prices,
    )

    with pytest.raises(BookNotFoundError):
        use_case.execute(an_offer())

    assert offers.by_id == {}
    assert prices.points == []


def test_a_long_book_title_is_cut_to_fit_the_offer(world):
    _, offers, prices, _ = world
    long_title = "A" * 300
    use_case = IngestOfferUseCase(
        get_book=GetOrCreateBookByIsbnUseCase(
            InMemoryProducts(),
            FakeMetadata(BookMetadata(isbn13=ISBN13, title=long_title)),
        ),
        offers=offers,
        prices=prices,
    )

    result = use_case.execute(an_offer())

    assert len(result.offer.title) == 255
    assert result.book.title == long_title
