import pytest

from src.collectors.api_sink import ApiOfferSink
from src.collectors.offers import CollectedOffer


class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code, self._body, self.text = status, body or {}, str(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        assert self.status_code < 400


class FakeSession:
    def __init__(self, post_status=201):
        self.headers, self.gets, self.posts = {}, [], []
        self.post_status = post_status

    def get(self, url, timeout):
        self.gets.append(url)
        return FakeResponse(200, {"data": {"id": "4", "type": "source_websites"}})

    def post(self, url, json, timeout):
        self.posts.append((url, json))
        return FakeResponse(self.post_status, {"errors": [{"detail": "bad"}]})


OFFER = CollectedOffer(
    isbn="9788535914849",
    url="https://www.estantevirtual.com.br/livro/x?condition=usado",
    price=17.5,
    condition="used",
)


def test_posts_a_jsonapi_offer_with_the_store_id():
    session = FakeSession()
    sink = ApiOfferSink("http://api/", "tok", session=session)

    sink.send("estante_virtual", OFFER)
    sink.send("estante_virtual", OFFER)

    assert session.headers["Authorization"] == "Bearer tok"
    assert session.gets == ["http://api/source-websites/name/estante_virtual"]
    url, body = session.posts[0]
    assert url == "http://api/offers/"
    assert body == {
        "data": {
            "type": "offers",
            "attributes": {
                "isbn": "9788535914849",
                "source_website_id": 4,
                "url": OFFER.url,
                "price": 17.5,
                "condition": "used",
                "is_available": True,
                "city": None,
                "state": None,
            },
        }
    }


def test_a_rejected_offer_raises():
    sink = ApiOfferSink("http://api", "tok", session=FakeSession(post_status=422))

    with pytest.raises(RuntimeError, match="422"):
        sink.send("estante_virtual", OFFER)
