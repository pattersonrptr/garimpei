from passlib.context import CryptContext

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.ports import UserRepositoryInterface
from src.app.interfaces.http.schemas.user_schema import (
    UserCreateRequest,  # , UserUpdate
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CreateUserUseCase:
    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def execute(self, user_data: UserCreateRequest, hashed_password: str) -> UserEntity:
        attrs = user_data.data.attributes
        # existing_user_by_username = self.user_repo.get_by_username(user_data.username)
        # if existing_user_by_username:
        #     raise ValueError("Username already registered")

        # existing_user_by_email = self.user_repo.get_by_email(user_data.email)
        # if existing_user_by_email:
        #     raise ValueError("Email already registered")

        new_user_entity = UserEntity(
            username=attrs.username,
            email=attrs.email,
            hashed_password=hashed_password,
            is_active=attrs.is_active if attrs.is_active is not None else True,
            is_staff=attrs.is_staff if attrs.is_staff is not None else False,
            is_superuser=attrs.is_superuser
            if attrs.is_superuser is not None
            else False,
        )
        created_user = self.user_repo.create(new_user_entity)
        return created_user


class GetUserByIdUseCase:
    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def execute(self, user_id: int) -> UserEntity | None:
        return self.user_repo.get_by_id(user_id)


class GetUserByUsernameUseCase:
    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def execute(self, username: str) -> UserEntity | None:
        return self.user_repo.get_by_username(username)


class GetUserByEmailUseCase:
    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def execute(self, email: str) -> UserEntity | None:
        return self.user_repo.get_by_email(email)


class GetAllUsersUseCase:
    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def execute(self) -> list[UserEntity]:
        return self.user_repo.get_all()


class UpdateUserUseCase:
    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def execute(self, user_id: int, user_data) -> UserEntity | None:
        """
        Updates a user with the provided data.
        Only non-None fields are updated.
        """
        existing_user = self.user_repo.get_by_id(user_id)
        if not existing_user:
            return None

        attrs = user_data.data.attributes

        # Update only provided fields (non-None)
        if attrs.username is not None:
            existing_user.username = attrs.username
        if attrs.email is not None:
            existing_user.email = attrs.email
        if attrs.is_active is not None:
            existing_user.is_active = attrs.is_active
        if attrs.is_staff is not None:
            existing_user.is_staff = attrs.is_staff
        if attrs.is_superuser is not None:
            existing_user.is_superuser = attrs.is_superuser

        updated_user = self.user_repo.update(user_id, existing_user)
        return updated_user


class DeleteUserUseCase:
    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def execute(self, user_id: int) -> bool:
        """
        Deletes a user.
        Returns True if successfully deleted, False if not found.
        """
        return self.user_repo.delete(user_id)
