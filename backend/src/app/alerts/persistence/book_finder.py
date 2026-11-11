"""BookFinder over the catalog: an alert's ISBN to the catalog's book."""

from sqlalchemy.orm import Session

from src.app.alerts.entities import BookRef
from src.app.alerts.ports import BookFinder
from src.app.catalog.entities import IdentifierKind
from src.app.catalog.isbn import InvalidIsbnError, normalize_isbn
from src.app.catalog.persistence.repositories import CanonicalProductRepository


class CatalogBookFinder(BookFinder):
    def __init__(self, db: Session):
        self.books = CanonicalProductRepository(db)

    def find_by_isbn(self, isbn: str) -> BookRef | None:
        try:
            isbn13 = normalize_isbn(isbn)
        except InvalidIsbnError:
            return None
        book = self.books.get_by_identifier(IdentifierKind.ISBN13, isbn13)
        if book is None or book.id is None:
            return None
        return BookRef(id=book.id, isbn13=isbn13, title=book.title)
