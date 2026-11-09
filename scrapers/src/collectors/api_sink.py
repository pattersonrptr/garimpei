"""Sends collected offers to the backend's POST /offers (architecture rule 5:
collectors never write to the database)."""

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
    def __init__(
        self,
        base_url: str,
        token: str,
        session: requests.Session | None = None,
        timeout: float = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": JSONAPI}
        )
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
        response = self.session.post(
            f"{self.base_url}/offers/",
            json={"data": {"type": "offers", "attributes": attributes}},
            timeout=self.timeout,
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"POST /offers {response.status_code}: {response.text[:200]}"
            )

    def _store_id(self, store_name: str) -> int:
        if store_name not in self._store_ids:
            response = self.session.get(
                f"{self.base_url}/source-websites/name/{store_name}",
                timeout=self.timeout,
            )
            response.raise_for_status()
            self._store_ids[store_name] = int(response.json()["data"]["id"])
        return self._store_ids[store_name]
