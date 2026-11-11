from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.app.entities.user import User as UserEntity
from src.app.infrastructure.database.models.user_model import User as UserModel
from src.app.interfaces.repositories.user_repository import UserRepositoryInterface


class UserRepository(UserRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, user: UserEntity) -> UserEntity:
        db_user = UserModel(**user.model_dump())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return UserEntity(**db_user.__dict__)

    def get_by_id(self, user_id: int) -> UserEntity | None:
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            return UserEntity(**user.__dict__)
        return None

    def get_by_username(self, username: str) -> UserEntity | None:
        user = self.db.query(UserModel).filter(UserModel.username == username).first()
        if user:
            return UserEntity(**user.__dict__)
        return None

    def get_by_email(self, email: str) -> UserEntity | None:
        # E-mail addresses are compared without case: "Ana@x.com" is "ana@x.com".
        user = (
            self.db.query(UserModel)
            .filter(func.lower(UserModel.email) == email.strip().lower())
            .first()
        )
        if user:
            return UserEntity(**user.__dict__)
        return None

    def get_all(self) -> list[UserEntity]:
        users = self.db.query(UserModel).all()
        return [UserEntity(**user.__dict__) for user in users]

    def update(self, user_id: int, user: UserEntity) -> UserEntity | None:
        db_user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not db_user:
            return None
        try:
            for key, value in user.model_dump(exclude_unset=True).items():
                setattr(db_user, key, value)
            db_user.updated_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(db_user)
            return UserEntity(**db_user.__dict__)
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
        except Exception as e:
            self.db.rollback()
            raise e
