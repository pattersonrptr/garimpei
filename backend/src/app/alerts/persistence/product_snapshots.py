"""ProductSnapshotReader over the catalog: the product each alert watches,
with today's lowest price per condition and the price verdict."""

from sqlalchemy.orm import Session

from src.app.alerts.entities import OfferPrice, ProductSnapshot
from src.app.alerts.ports import ProductSnapshotReader
from src.app.catalog.entities import BookDetail, IdentifierKind, ProductCondition
from src.app.catalog.persistence.models import (
    CanonicalProduct as CanonicalProductModel,
)
from src.app.catalog.persistence.models import (
    ProductIdentifier as ProductIdentifierModel,
)
from src.app.catalog.persistence.repositories import BookCatalogRepository
from src.app.catalog.use_cases import JudgeBookPricesUseCase

CONDITIONS = (ProductCondition.NEW, ProductCondition.USED)


def _lowest(book: BookDetail, condition: ProductCondition) -> OfferPrice | None:
    offers = [
        o
        for o in book.offers
        if o.condition == condition and o.is_available and o.price is not None
    ]
    best = min(offers, key=lambda o: o.price or 0, default=None)
    return (
        OfferPrice(price=best.price, store=best.store) if best and best.price else None
    )


class CatalogProductSnapshots(ProductSnapshotReader):
    """One catalog read per product: fine for the handful of alerts a user has."""

    def __init__(self, db: Session):
        self.db = db
        self.books = BookCatalogRepository(db)

    def snapshots(self, product_ids: list[int]) -> dict[int, ProductSnapshot]:
        if not product_ids:
            return {}
        rows = (
            self.db.query(
                CanonicalProductModel.id,
                CanonicalProductModel.category,
                CanonicalProductModel.title,
                ProductIdentifierModel.value,
            )
            .outerjoin(
                ProductIdentifierModel,
                (
                    ProductIdentifierModel.canonical_product_id
                    == CanonicalProductModel.id
                )
                & (ProductIdentifierModel.kind == IdentifierKind.ISBN13.value),
            )
            .filter(CanonicalProductModel.id.in_(product_ids))
            .all()
        )
        judge = JudgeBookPricesUseCase(self.books)
        found: dict[int, ProductSnapshot] = {}
        for product_id, category, title, isbn13 in rows:
            book = self.books.get_book(isbn13) if isbn13 else None
            if book is None:
                found[product_id] = ProductSnapshot(
                    id=product_id, category=category, title=title, isbn13=isbn13
                )
                continue
            lowest = {c.value: p for c in CONDITIONS if (p := _lowest(book, c))}
            verdicts = {v.condition.value: v.status.value for v in judge.execute(book)}
            found[product_id] = ProductSnapshot(
                id=product_id,
                category=category,
                title=book.title,
                isbn13=isbn13,
                cover_url=book.attributes.get("cover_url"),
                lowest=lowest,
                verdicts=verdicts,
            )
        return found
