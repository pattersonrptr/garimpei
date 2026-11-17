"""Builds accounts' repository and the use cases other modules read.

Accounts' controllers and the logged-in-user dependency get the user
repository here, and alerts reads an alert's owner through
``user_by_id``, so none of them builds the SQLAlchemy repository itself.
"""

from sqlalchemy.orm import Session

from src.app.accounts.persistence.repositories import UserRepository
from src.app.accounts.ports import UserRepositoryInterface
from src.app.accounts.use_cases import GetUserByIdUseCase


def users(db: Session) -> UserRepositoryInterface:
    return UserRepository(db)


def user_by_id(db: Session) -> GetUserByIdUseCase:
    """Looks a user up by id; what other modules need from accounts."""
    return GetUserByIdUseCase(users(db))
