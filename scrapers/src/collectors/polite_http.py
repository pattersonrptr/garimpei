"""A slow, well-behaved HTTP client for collectors (posture rule 9).

- Respects robots.txt (read once per host).
- One fixed, real browser User-Agent; one session, so cookies are kept.
- A random pause before every request except the first.
- 403 and 429 mean "blocked": the caller stops the store for the day.
  Nothing here tries to get past a block.
"""

import logging
import random
import time
from collections.abc import Callable
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

from src.collectors.ports import (
    PageFetcher,
    StoreBlockedError,
    StoreUnavailableError,
)

logger = logging.getLogger(__name__)

# A real browser's User-Agent, kept fixed: rotating it from one IP looks more
# like a bot, not less.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


class PoliteHttpClient(PageFetcher):
    def __init__(
        self,
        *,
        user_agent: str = BROWSER_USER_AGENT,
        pause: tuple[float, float] = (5.0, 15.0),
        timeout: float = 30.0,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        uniform: Callable[[float, float], float] = random.uniform,
    ):
        self.user_agent = user_agent
        self.pause = pause
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,"
                "*/*;q=0.8",
            }
        )
        self._sleep = sleep
        self._uniform = uniform
        self._robots: dict[str, RobotFileParser] = {}
        self._first = True

    def get(self, url: str) -> str:
        """The body of ``url``. Raises StoreBlockedError or StoreUnavailableError."""
        if not self._robots_for(url).can_fetch(self.user_agent, url):
            raise StoreBlockedError(f"robots.txt disallows {url}")
        response = self._request(url)
        if response.status_code in (403, 429):
            raise StoreBlockedError(f"HTTP {response.status_code} on {url}")
        if response.status_code >= 400:
            raise StoreUnavailableError(f"HTTP {response.status_code} on {url}")
        if not response.text.strip():
            raise StoreBlockedError(f"empty page on {url}")
        return response.text

    def _request(self, url: str) -> requests.Response:
        if not self._first:
            self._sleep(self._uniform(*self.pause))
        self._first = False
        try:
            return self.session.get(url, timeout=self.timeout)
        except requests.RequestException as e:
            raise StoreUnavailableError(f"{type(e).__name__} on {url}") from e

    def _robots_for(self, url: str) -> RobotFileParser:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            parser = RobotFileParser()
            response = self._request(f"{host}/robots.txt")
            if response.status_code in (401, 403):
                parser.disallow_all = True
            elif response.status_code >= 400:
                parser.allow_all = True  # no robots.txt: nothing is disallowed
            else:
                parser.parse(response.text.splitlines())
            self._robots[host] = parser
        return self._robots[host]
