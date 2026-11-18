"""Builds stores' use cases from a database session.

Other modules reach stores through these factories (and adapt the use cases
to their own ports), never through stores' repository.
"""

from sqlalchemy.orm import Session

from src.app.stores.persistence.repositories import StoreRepository
from src.app.stores.use_cases import GetStoreByNameUseCase, GetStoreUseCase


def store_by_id(db: Session) -> GetStoreUseCase:
    return GetStoreUseCase(StoreRepository(db))


def store_by_name(db: Session) -> GetStoreByNameUseCase:
    return GetStoreByNameUseCase(StoreRepository(db))
