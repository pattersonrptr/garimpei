"""BrasilApiBookMetadata against a fake HTTP client (no network)."""

import pytest
import requests

from src.app.catalog.adapters.brasilapi_books import BASE_URL, BrasilApiBookMetadata
from src.app.catalog.ports import BookMetadataUnavailableError

ISBN13 = "9788535914849"

# Shape of a real answer from https://brasilapi.com.br/api/isbn/v1/9788535914849
SAMPLE = {
    "isbn": ISBN13,
    "title": "1984",
    "subtitle": None,
    "authors": ["George Orwell", "Alexandre Hubner", "Heloisa Jahn"],
    "publisher": "Companhia das Letras",
    "synopsis": "Publicada originalmente em 1949.\n",
    "dimensions": {"width": 13, "height": 21, "unit": "CENTIMETER"},
    "year": 2009,
    "format": "PHYSICAL",
    "page_count": 416,
    "subjects": ["Literatura", "Literatura"],
    "location": "São Paulo, SP",
    "retail_price": None,
    "cover_url": None,
    "provider": "cbl",
}


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=False):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("not json")
        return self._payload


class FakeHttp:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests: list[tuple[str, float]] = []

    def get(self, url, timeout):
        self.requests.append((url, timeout))
        if self.error:
            raise self.error
        return self.response


def test_maps_a_full_answer_to_book_metadata():
    http = FakeHttp(FakeResponse(payload=SAMPLE))

    book = BrasilApiBookMetadata(http=http, timeout=3).fetch(ISBN13)

    assert http.requests == [(f"{BASE_URL}/{ISBN13}", 3)]
    assert book.isbn13 == ISBN13
    assert book.title == "1984"
    assert book.subtitle is None
    assert book.authors == ("George Orwell", "Alexandre Hubner", "Heloisa Jahn")
    assert book.publisher == "Companhia das Letras"
    assert book.year == 2009
    assert book.page_count == 416
    assert book.synopsis == "Publicada originalmente em 1949."
    assert book.cover_url is None


@pytest.mark.parametrize("status", [400, 404])
def test_unknown_or_rejected_isbn_means_the_source_has_no_such_book(status):
    http = FakeHttp(FakeResponse(status, {"message": "ISBN inválido"}))

    assert BrasilApiBookMetadata(http=http).fetch(ISBN13) is None


def test_an_answer_without_a_title_is_treated_as_unknown():
    http = FakeHttp(FakeResponse(payload={**SAMPLE, "title": "  "}))

    assert BrasilApiBookMetadata(http=http).fetch(ISBN13) is None


def test_odd_field_types_are_ignored_instead_of_crashing():
    payload = {**SAMPLE, "year": "2009", "page_count": True, "authors": "Orwell"}
    http = FakeHttp(FakeResponse(payload=payload))

    book = BrasilApiBookMetadata(http=http).fetch(ISBN13)

    assert book.year is None
    assert book.page_count is None
    assert book.authors == ()


@pytest.mark.parametrize("status", [429, 500, 503])
def test_server_errors_are_reported_as_unavailable(status):
    http = FakeHttp(FakeResponse(status))

    with pytest.raises(BookMetadataUnavailableError, match=str(status)):
        BrasilApiBookMetadata(http=http).fetch(ISBN13)


def test_network_failures_are_reported_as_unavailable():
    http = FakeHttp(error=requests.Timeout("slow"))

    with pytest.raises(BookMetadataUnavailableError):
        BrasilApiBookMetadata(http=http).fetch(ISBN13)


def test_invalid_json_is_reported_as_unavailable():
    http = FakeHttp(FakeResponse(json_error=True))

    with pytest.raises(BookMetadataUnavailableError):
        BrasilApiBookMetadata(http=http).fetch(ISBN13)
