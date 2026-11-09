"""ISBN rules (pure): normalize any valid ISBN-10 or ISBN-13 to ISBN-13."""

import re


class InvalidIsbnError(ValueError):
    """The text is not a valid ISBN-10 or ISBN-13."""


def _isbn13_is_valid(digits: str) -> bool:
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    return total % 10 == 0


def _isbn10_is_valid(chars: str) -> bool:
    values = [10 if c == "X" else int(c) for c in chars]
    return sum((10 - i) * v for i, v in enumerate(values)) % 11 == 0


def _isbn10_to_isbn13(isbn10: str) -> str:
    body = "978" + isbn10[:9]
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(body))
    return body + str((10 - total % 10) % 10)


def normalize_isbn(raw: str) -> str:
    """Return the ISBN-13 for ``raw`` (hyphens and spaces are ignored).

    Raises InvalidIsbnError when the length, characters or check digit are wrong.
    """
    text = re.sub(r"[\s-]", "", raw or "").upper()
    if re.fullmatch(r"\d{13}", text):
        if text[:3] in ("978", "979") and _isbn13_is_valid(text):
            return text
    elif re.fullmatch(r"\d{9}[\dX]", text) and _isbn10_is_valid(text):
        return _isbn10_to_isbn13(text)
    raise InvalidIsbnError(f"Not a valid ISBN: {raw!r}")
