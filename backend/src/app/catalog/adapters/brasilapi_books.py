"""Book metadata from BrasilAPI (https://brasilapi.com.br/api/isbn/v1/{isbn}).

BrasilAPI itself asks CBL, Mercado Editorial, Open Library and Google Books.
This adapter plugs into the catalog through BookMetadataGateway.
"""

import requests

from src.app.catalog.entities import BookMetadata
from src.app.catalog.ports import BookMetadataGateway, BookMetadataUnavailableError

BASE_URL = "https://brasilapi.com.br/api/isbn/v1"
DEFAULT_TIMEOUT_SECONDS = 10.0


def _text(value: object) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _number(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class BrasilApiBookMetadata(BookMetadataGateway):
    """BookMetadataGateway backed by BrasilAPI."""

    def __init__(self, http=requests, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.http = http
        self.timeout = timeout

    def fetch(self, isbn13: str) -> BookMetadata | None:
        try:
            response = self.http.get(f"{BASE_URL}/{isbn13}", timeout=self.timeout)
        except requests.RequestException as exc:
            raise BookMetadataUnavailableError(
                f"BrasilAPI request failed: {exc}"
            ) from exc

        # 400 ("ISBN inválido") and 404 both mean this source has no such book.
        if response.status_code in (400, 404):
            return None
        if response.status_code != 200:
            raise BookMetadataUnavailableError(
                f"BrasilAPI answered {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise BookMetadataUnavailableError("BrasilAPI sent invalid JSON") from exc

        title = _text(data.get("title"))
        if not title:
            return None

        authors = data.get("authors")
        return BookMetadata(
            isbn13=isbn13,
            title=title,
            subtitle=_text(data.get("subtitle")),
            authors=tuple(a.strip() for a in authors if _text(a))
            if isinstance(authors, list)
            else (),
            publisher=_text(data.get("publisher")),
            year=_number(data.get("year")),
            page_count=_number(data.get("page_count")),
            synopsis=_text(data.get("synopsis")),
            cover_url=_text(data.get("cover_url")),
        )
