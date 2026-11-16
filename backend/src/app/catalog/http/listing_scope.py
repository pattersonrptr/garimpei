"""The ListingScope catalog's HTTP layer hands to its product repository.

Catalog does not know which module implements its ``ListingScope`` port; the
composition root (``src/app/composition.py``) registers it at start-up.
"""

from src.app.catalog.ports import ListingScope

_scope: ListingScope | None = None


def use_listing_scope(scope: ListingScope) -> None:
    """Register the ListingScope (called once by the composition root)."""
    global _scope
    _scope = scope


def get_listing_scope() -> ListingScope:
    """FastAPI dependency: the registered ListingScope."""
    if _scope is None:
        raise RuntimeError(
            "No ListingScope registered; src/app/composition.py compose() "
            "must run at start-up"
        )
    return _scope
