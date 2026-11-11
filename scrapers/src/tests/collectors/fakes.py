"""Fakes shared by the collector tests (no network)."""

import json

from src.collectors.offers import CollectedOffer
from src.collectors.ports import (
    CollectionQueue,
    OfferSink,
    OfferSource,
    PageFetcher,
    StoreRunLog,
    StoreRunState,
)


def page_with_state(state: dict) -> str:
    """An HTML page shaped like Estante Virtual's: state JSON in a script."""
    return (
        "<html><head></head><body><div id='app'></div>"
        f"<script>window.__INITIAL_STATE__ = {json.dumps(state)};</script>"
        "</body></html>"
    )


class PagesByUrl(PageFetcher):
    def __init__(self, pages: dict[str, str]):
        self.pages, self.calls = pages, []

    def get(self, url):
        self.calls.append(url)
        return self.pages[url]


class ScriptedSource(OfferSource):
    """Answers per ISBN with a list of offers or raises an exception."""

    store_name = "Test Store"

    def __init__(self, answers: dict):
        self.answers, self.asked = answers, []

    def find_offers(self, isbn13):
        self.asked.append(isbn13)
        answer = self.answers.get(isbn13, [])
        if isinstance(answer, Exception):
            raise answer
        return answer


class RecordingSink(OfferSink):
    def __init__(self, failing_urls=()):
        self.sent, self.failing_urls = [], set(failing_urls)

    def send(self, store_name, offer: CollectedOffer):
        if offer.url in self.failing_urls:
            raise RuntimeError("422")
        self.sent.append((store_name, offer))


class FixedQueue(CollectionQueue):
    """The same ISBNs for every store, or an error."""

    def __init__(self, isbns=(), error=None):
        self.isbns, self.error, self.asked = list(isbns), error, []

    def isbns_for(self, store_name):
        self.asked.append(store_name)
        if self.error:
            raise self.error
        return self.isbns


class InMemoryRunLog(StoreRunLog):
    def __init__(self, states=None):
        self.states = dict(states or {})

    def get(self, store_name):
        return self.states.get(store_name, StoreRunState())

    def save(self, store_name, state):
        self.states[store_name] = state
