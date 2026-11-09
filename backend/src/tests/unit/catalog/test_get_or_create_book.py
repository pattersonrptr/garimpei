"""GetOrCreateBookByIsbnUseCase, tested with in-memory doubles for both ports."""

import pytest

from src.app.catalog.entities import (
    BookMetadata,
    CanonicalProduct,
    IdentifierKind,
    ProductCategory,
)
from src.app.catalog.isbn import InvalidIsbnError
from src.app.catalog.ports import (
    BookMetadataGateway,
    BookMetadataUnavailableError,
    CanonicalProductRepositoryInterface,
)
from src.app.catalog.use_cases import BookNotFoundError, GetOrCreateBookByIsbnUseCase

ISBN13 = "9788535914849"


class InMemoryProducts(CanonicalProductRepositoryInterface):
    def __init__(self):
        self.stored: list[CanonicalProduct] = []

    def get_by_identifier(self, kind, value):
        for product in self.stored:
            if any(i.kind == kind and i.value == value for i in product.identifiers):
                return product
        return None

    def create(self, product):
        product.id = len(self.stored) + 1
        self.stored.append(product)
        return product


class FakeMetadata(BookMetadataGateway):
    def __init__(self, book=None, error=None):
        self.book = book
        self.error = error
        self.calls: list[str] = []

    def fetch(self, isbn13):
        self.calls.append(isbn13)
        if self.error:
            raise self.error
        return self.book


@pytest.fixture
def book_1984():
    return BookMetadata(
        isbn13=ISBN13,
        title="1984",
        authors=("George Orwell",),
        publisher="Companhia das Letras",
        year=2009,
        page_count=416,
    )


def test_creates_the_book_from_its_metadata_when_it_is_new(book_1984):
    products, metadata = InMemoryProducts(), FakeMetadata(book_1984)

    book = GetOrCreateBookByIsbnUseCase(products, metadata).execute("978-85-359-1484-9")

    assert book.id == 1
    assert book.category == ProductCategory.BOOK
    assert book.title == "1984"
    assert book.attributes == {
        "authors": ["George Orwell"],
        "publisher": "Companhia das Letras",
        "year": 2009,
        "page_count": 416,
    }
    assert [(i.kind, i.value) for i in book.identifiers] == [
        (IdentifierKind.ISBN13, ISBN13)
    ]
    assert metadata.calls == [ISBN13]


def test_reuses_the_existing_book_without_asking_the_metadata_source(book_1984):
    products, metadata = InMemoryProducts(), FakeMetadata(book_1984)
    use_case = GetOrCreateBookByIsbnUseCase(products, metadata)
    first = use_case.execute(ISBN13)

    second = use_case.execute("8535914846")  # same book, as an ISBN-10

    assert second is first
    assert len(products.stored) == 1
    assert metadata.calls == [ISBN13]  # only the first lookup went out


def test_an_invalid_isbn_is_rejected_before_any_lookup():
    products, metadata = InMemoryProducts(), FakeMetadata()

    with pytest.raises(InvalidIsbnError):
        GetOrCreateBookByIsbnUseCase(products, metadata).execute("9788535914848")

    assert metadata.calls == []
    assert products.stored == []


def test_a_book_no_source_knows_is_not_stored():
    products, metadata = InMemoryProducts(), FakeMetadata(book=None)

    with pytest.raises(BookNotFoundError):
        GetOrCreateBookByIsbnUseCase(products, metadata).execute(ISBN13)

    assert products.stored == []


def test_a_failing_source_is_reported_and_nothing_is_stored():
    products = InMemoryProducts()
    metadata = FakeMetadata(error=BookMetadataUnavailableError("timeout"))

    with pytest.raises(BookMetadataUnavailableError):
        GetOrCreateBookByIsbnUseCase(products, metadata).execute(ISBN13)

    assert products.stored == []


def test_empty_metadata_fields_are_left_out_of_the_attributes():
    sparse = BookMetadata(isbn13=ISBN13, title="Sem Dados")
    products, metadata = InMemoryProducts(), FakeMetadata(sparse)

    book = GetOrCreateBookByIsbnUseCase(products, metadata).execute(ISBN13)

    assert book.attributes == {}
