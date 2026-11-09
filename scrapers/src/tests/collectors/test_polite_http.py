import pytest
import requests

from src.collectors.polite_http import BROWSER_USER_AGENT, PoliteHttpClient
from src.collectors.ports import StoreBlockedError, StoreUnavailableError

ROBOTS = "User-agent: *\nDisallow: /checkout\n"


class FakeResponse:
    def __init__(self, status=200, text="<html>ok</html>"):
        self.status_code, self.text = status, text


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls, self.headers = responses, [], {}

    def get(self, url, timeout):
        self.calls.append(url)
        answer = self.responses.get(url, FakeResponse())
        if isinstance(answer, Exception):
            raise answer
        return answer


def client(responses, robots=None):
    robots = robots or FakeResponse(text=ROBOTS)
    session = FakeSession({"https://store.test/robots.txt": robots, **responses})
    pauses = []
    http = PoliteHttpClient(
        session=session, sleep=pauses.append, uniform=lambda a, b: (a + b) / 2
    )
    return http, session, pauses


def test_reads_a_page_with_a_fixed_browser_user_agent():
    http, session, _ = client({})

    assert http.get("https://store.test/busca?q=1") == "<html>ok</html>"
    assert session.headers["User-Agent"] == BROWSER_USER_AGENT


def test_pauses_before_every_request_but_the_first():
    http, session, pauses = client({})

    http.get("https://store.test/a")
    http.get("https://store.test/b")

    assert session.calls == [
        "https://store.test/robots.txt",
        "https://store.test/a",
        "https://store.test/b",
    ]
    assert pauses == [10.0, 10.0]  # robots.txt read once, then one pause each


def test_robots_txt_is_respected():
    http, session, _ = client({})

    with pytest.raises(StoreBlockedError, match="robots.txt"):
        http.get("https://store.test/checkout")
    assert "https://store.test/checkout" not in session.calls


def test_a_missing_robots_txt_allows_everything():
    http, _, _ = client({}, robots=FakeResponse(status=404, text=""))

    assert http.get("https://store.test/checkout")


@pytest.mark.parametrize("status", [403, 429])
def test_forbidden_or_too_many_requests_is_a_block(status):
    http, _, _ = client({"https://store.test/a": FakeResponse(status=status)})

    with pytest.raises(StoreBlockedError, match=str(status)):
        http.get("https://store.test/a")


def test_an_empty_page_is_a_block():
    http, _, _ = client({"https://store.test/a": FakeResponse(text="  ")})

    with pytest.raises(StoreBlockedError, match="empty"):
        http.get("https://store.test/a")


@pytest.mark.parametrize(
    "answer", [FakeResponse(status=503), requests.ConnectionError("down")]
)
def test_server_or_network_errors_mean_unavailable(answer):
    http, _, _ = client({"https://store.test/a": answer})

    with pytest.raises(StoreUnavailableError):
        http.get("https://store.test/a")
