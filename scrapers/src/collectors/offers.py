from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class CollectedOffer:
    """One offer as a store shows it. Only what the scraping rule allows:
    price, link, condition, availability and seller city. The book's own data
    comes from its metadata, not from stores."""

    isbn: str
    url: str
    price: float
    condition: str  # "new" or "used", the backend's ProductCondition values
    is_available: bool = True
    city: str | None = None
    state: str | None = None
