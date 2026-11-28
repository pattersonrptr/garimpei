"""Builds stores' repository and use cases from a database session.

Other modules reach stores through these factories (and adapt the use cases
to their own ports), never through stores' repository.
"""

from sqlalchemy.orm import Session

from src.app.stores.persistence.repositories import StoreRepository
from src.app.stores.ports import StoreRepositoryInterface
from src.app.stores.use_cases import (
    CountStoresUseCase,
    GetStoreByNameUseCase,
    GetStoreUseCase,
)


def stores(db: Session) -> StoreRepositoryInterface:
    """Stores' repository, for stores' own controller."""
    return StoreRepository(db)


def store_by_id(db: Session) -> GetStoreUseCase:
    return GetStoreUseCase(StoreRepository(db))


def store_by_name(db: Session) -> GetStoreByNameUseCase:
    return GetStoreByNameUseCase(StoreRepository(db))


def count_stores(db: Session) -> CountStoresUseCase:
    """How many stores there are (the admin summary)."""
    return CountStoresUseCase(StoreRepository(db))
