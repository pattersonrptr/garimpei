"""Matching strategies: how a piece of text is recognized as a known identifier.

One strategy per category. A new category adds a matcher; the use cases do not
change.
"""

from src.app.catalog.entities import IdentifierKind, ProductCategory, ProductIdentifier
from src.app.catalog.isbn import InvalidIsbnError, normalize_isbn


class IsbnMatcher:
    """Books: the ISBN is the identity."""

    category = ProductCategory.BOOK

    def identify(self, text: str) -> ProductIdentifier | None:
        """The ISBN-13 identifier for ``text``, or None if it is not an ISBN."""
        try:
            return ProductIdentifier(
                kind=IdentifierKind.ISBN13, value=normalize_isbn(text)
            )
        except InvalidIsbnError:
            return None
