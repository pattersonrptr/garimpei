"""Builds catalog's adapters and composed use cases.

Catalog's controllers call these factories with the request's database
session, so they depend on catalog's ports and use cases, never on the
concrete repositories or the book metadata client.
"""

from sqlalchemy.orm import Session

from src.app.catalog.adapters.brasilapi_books import BrasilApiBookMetadata
from src.app.catalog.adapters.stores import StoreDirectoryOverStores
from src.app.catalog.persistence.repositories import (
    BookCatalogRepository,
    CanonicalProductRepository,
    PriceHistoryRepository,
    ProductRepository,
)
from src.app.catalog.ports import (
    BookCatalogReader,
    BookMetadataGateway,
    ListingScope,
    PriceHistoryRepositoryInterface,
    ProductRepositoryInterface,
    StoreDirectory,
)
from src.app.catalog.use_cases import (
    CountProductsUseCase,
    GetOrCreateBookByIsbnUseCase,
    IngestOfferUseCase,
    ListCollectionQueueUseCase,
)
from src.app.stores import wiring as stores_wiring


def products(
    db: Session, scope: ListingScope | None = None
) -> ProductRepositoryInterface:
    """Listings; ``scope`` narrows lists to what alerts found."""
    return ProductRepository(db, scope)


def price_histories(db: Session) -> PriceHistoryRepositoryInterface:
    return PriceHistoryRepository(db)


def book_catalog(db: Session) -> BookCatalogReader:
    """The read model behind the public book pages."""
    return BookCatalogRepository(db)


def stores(db: Session) -> StoreDirectory:
    """The stores offers come from (over the stores module)."""
    return StoreDirectoryOverStores(
        stores_wiring.store_by_id(db), stores_wiring.store_by_name(db)
    )


def book_metadata() -> BookMetadataGateway:
    """Where a new ISBN's title and authors come from."""
    return BrasilApiBookMetadata()


def ingest_offer(db: Session, metadata: BookMetadataGateway) -> IngestOfferUseCase:
    """A collector's offer: the book (created from its ISBN), the listing and
    its price point."""
    return IngestOfferUseCase(
        get_book=GetOrCreateBookByIsbnUseCase(CanonicalProductRepository(db), metadata),
        offers=ProductRepository(db),
        prices=PriceHistoryRepository(db),
    )


def collection_queue(db: Session) -> ListCollectionQueueUseCase:
    """The books the daily collection should look up next."""
    return ListCollectionQueueUseCase(CanonicalProductRepository(db))


def count_products(db: Session) -> CountProductsUseCase:
    """How many products there are (the admin summary)."""
    return CountProductsUseCase(ProductRepository(db))
