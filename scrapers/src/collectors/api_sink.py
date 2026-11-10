"""Sends collected offers to the backend's POST /offers (architecture rule 5:
collectors never write to the database)."""

from collections.abc import Callable

import requests

from src.collectors.offers import CollectedOffer
from src.collectors.ports import OfferSink

JSONAPI = "application/vnd.api+json"


def login(base_url: str, username: str, password: str, timeout: float = 10) -> str:
    """A staff access token for the collector's service account."""
    response = requests.post(
        f"{base_url}/auth/login",
        data={"username": username, "password": password, "grant_type": "password"},
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    token = body.get("data", {}).get("attributes", {}).get("access_token") or body.get(
        "access_token"
    )
    if not token:
        raise RuntimeError("login answered without an access token")
    return token


class ApiOfferSink(OfferSink):
    """Access tokens expire (30 min by default) and a run over many books is
    longer than that, so a 401 logs in again once and repeats the request."""

    def __init__(
        self,
        base_url: str,
        authenticate: Callable[[], str],
        session: requests.Session | None = None,
        timeout: float = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.authenticate = authenticate
        self.session = session or requests.Session()
        self.session.headers["Content-Type"] = JSONAPI
        self._use_token(authenticate())
        self.timeout = timeout
        self._store_ids: dict[str, int] = {}

    def send(self, store_name: str, offer: CollectedOffer) -> None:
        attributes = {
            "isbn": offer.isbn,
            "source_website_id": self._store_id(store_name),
            "url": offer.url,
            "price": offer.price,
            "condition": offer.condition,
            "is_available": offer.is_available,
            "city": offer.city,
            "state": offer.state,
        }
        response = self._request(
            "post",
            f"{self.base_url}/offers/",
            json={"data": {"type": "offers", "attributes": attributes}},
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"POST /offers {response.status_code}: {response.text[:200]}"
            )

    def _store_id(self, store_name: str) -> int:
        if store_name not in self._store_ids:
            response = self._request(
                "get", f"{self.base_url}/source-websites/name/{store_name}"
            )
            response.raise_for_status()
            self._store_ids[store_name] = int(response.json()["data"]["id"])
        return self._store_ids[store_name]

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        send = getattr(self.session, method)
        response = send(url, timeout=self.timeout, **kwargs)
        if response.status_code == 401:
            self._use_token(self.authenticate())
            response = send(url, timeout=self.timeout, **kwargs)
        return response

    def _use_token(self, token: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {token}"
