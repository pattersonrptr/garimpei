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
    """Answers POSTs with the given statuses in turn (the last one repeats)
    and records the token each request carried."""

    def __init__(self, *post_statuses):
        self.headers, self.gets, self.posts = {}, [], []
        self.post_statuses = list(post_statuses) or [201]

    def get(self, url, timeout):
        self.gets.append(url)
        return FakeResponse(200, {"data": {"id": "4", "type": "source_websites"}})

    def post(self, url, json, timeout):
        self.posts.append((url, json, self.headers["Authorization"]))
        status = (
            self.post_statuses.pop(0)
            if len(self.post_statuses) > 1
            else (self.post_statuses[0])
        )
        return FakeResponse(status, {"errors": [{"detail": "bad"}]})


def tokens(*values):
    """An authenticate() that hands out these tokens in order."""
    pending = list(values)
    return lambda: pending.pop(0)


OFFER = CollectedOffer(
    isbn="9788535914849",
    url="https://www.estantevirtual.com.br/livro/x?condition=usado",
    price=17.5,
    condition="used",
)


def test_posts_a_jsonapi_offer_with_the_store_id():
    session = FakeSession()
    sink = ApiOfferSink("http://api/", tokens("tok"), session=session)

    sink.send("estante_virtual", OFFER)
    sink.send("estante_virtual", OFFER)

    assert session.headers["Authorization"] == "Bearer tok"
    assert session.gets == ["http://api/source-websites/name/estante_virtual"]
    url, body, _ = session.posts[0]
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


def test_an_expired_token_logs_in_again_and_repeats_once():
    session = FakeSession(401, 201)
    sink = ApiOfferSink("http://api", tokens("old", "new"), session=session)

    sink.send("estante_virtual", OFFER)

    assert [auth for _, _, auth in session.posts] == ["Bearer old", "Bearer new"]


def test_a_401_after_logging_in_again_raises():
    session = FakeSession(401)
    sink = ApiOfferSink("http://api", tokens("old", "new"), session=session)

    with pytest.raises(RuntimeError, match="401"):
        sink.send("estante_virtual", OFFER)
    assert len(session.posts) == 2


def test_a_rejected_offer_raises():
    sink = ApiOfferSink("http://api", tokens("tok"), session=FakeSession(422))

    with pytest.raises(RuntimeError, match="422"):
        sink.send("estante_virtual", OFFER)
