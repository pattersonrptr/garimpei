from dataclasses import asdict, fields
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.persistence.models import User as UserModel
from src.app.accounts.ports import UserHasDataError, UserRepositoryInterface

_USER_FIELDS = [f.name for f in fields(UserEntity)]


def _to_entity(model: UserModel) -> UserEntity:
    return UserEntity(**{name: getattr(model, name) for name in _USER_FIELDS})


class UserRepository(UserRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, user: UserEntity) -> UserEntity:
        db_user = UserModel(**asdict(user))
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return _to_entity(db_user)

    def get_by_id(self, user_id: int) -> UserEntity | None:
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            return _to_entity(user)
        return None

    def get_by_username(self, username: str) -> UserEntity | None:
        user = self.db.query(UserModel).filter(UserModel.username == username).first()
        if user:
            return _to_entity(user)
        return None

    def get_by_email(self, email: str) -> UserEntity | None:
        # E-mail addresses are compared without case: "Ana@x.com" is "ana@x.com".
        user = (
            self.db.query(UserModel)
            .filter(func.lower(UserModel.email) == email.strip().lower())
            .first()
        )
        if user:
            return _to_entity(user)
        return None

    def get_all(self) -> list[UserEntity]:
        users = self.db.query(UserModel).all()
        return [_to_entity(user) for user in users]

    def count(self, active_only: bool = False) -> int:
        query = self.db.query(func.count(UserModel.id))
        if active_only:
            query = query.filter(UserModel.is_active.is_(True))
        return query.scalar() or 0

    def update(self, user_id: int, user: UserEntity) -> UserEntity | None:
        db_user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not db_user:
            return None
        try:
            values = asdict(user) | {"updated_at": datetime.now(UTC)}
            for key, value in values.items():
                setattr(db_user, key, value)
            self.db.commit()
            self.db.refresh(db_user)
            return _to_entity(db_user)
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, user_id: int) -> bool:
        db_user_model = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not db_user_model:
            return False
        try:
            self.db.delete(db_user_model)
            self.db.commit()
            return True
        except IntegrityError as e:
            self.db.rollback()
            raise UserHasDataError() from e
        except Exception as e:
            self.db.rollback()
            raise e
