from src.collectors.offers import CollectedOffer
from src.collectors.ports import StoreBlockedError, StoreUnavailableError
from src.collectors.use_cases import CollectOffers
from src.tests.collectors.fakes import RecordingSink, ScriptedSource


def offer(isbn, condition="used"):
    return CollectedOffer(
        isbn=isbn,
        url=f"https://store/{isbn}/{condition}",
        price=10.0,
        condition=condition,
    )


def test_every_offer_found_is_sent():
    source = ScriptedSource({"A": [offer("A", "new"), offer("A")], "B": [offer("B")]})
    sink = RecordingSink()

    report = CollectOffers(source, sink).execute(["A", "B"])

    assert report.sent == 3
    assert [o.url for _, o in sink.sent] == [
        "https://store/A/new",
        "https://store/A/used",
        "https://store/B/used",
    ]
    assert {name for name, _ in sink.sent} == {"Test Store"}


def test_a_book_the_store_does_not_have_is_reported():
    report = CollectOffers(ScriptedSource({}), RecordingSink()).execute(["A"])

    assert report.not_found == ["A"]
    assert report.failed == []


def test_a_block_stops_the_store_and_skips_the_rest():
    source = ScriptedSource({"A": [offer("A")], "B": StoreBlockedError("HTTP 429")})

    report = CollectOffers(source, RecordingSink()).execute(["A", "B", "C", "D"])

    assert source.asked == ["A", "B"]
    assert report.blocked == "HTTP 429"
    assert report.skipped == ["C", "D"]
    assert report.sent == 1


def test_an_unavailable_store_fails_that_isbn_and_goes_on():
    source = ScriptedSource({"A": StoreUnavailableError("timeout"), "B": [offer("B")]})

    report = CollectOffers(source, RecordingSink()).execute(["A", "B"])

    assert report.failed == [("A", "store unavailable: timeout")]
    assert report.sent == 1
    assert report.blocked is None


def test_a_failed_send_is_reported_and_the_rest_still_go():
    source = ScriptedSource({"A": [offer("A", "new"), offer("A")]})
    sink = RecordingSink(failing_urls={"https://store/A/new"})

    report = CollectOffers(source, sink).execute(["A"])

    assert report.sent == 1
    assert report.failed == [("A", "send failed: 422")]
