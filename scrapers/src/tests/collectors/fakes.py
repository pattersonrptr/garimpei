"""Fakes shared by the collector tests (no network)."""

import json

from src.collectors.offers import CollectedOffer
from src.collectors.ports import OfferSink, OfferSource, PageFetcher


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
