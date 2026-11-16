from dataclasses import dataclass

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.ports import UserRepositoryInterface


@dataclass(frozen=True, kw_only=True)
class NewUser:
    """What it takes to create an account (the password comes hashed apart)."""

    username: str
    email: str
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False


@dataclass(frozen=True, kw_only=True)
class UserChanges:
    """Fields to change on an account; None keeps the current value."""

    username: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_staff: bool | None = None
    is_superuser: bool | None = None


class CreateUserUseCase:
    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def execute(self, new_user: NewUser, hashed_password: str) -> UserEntity:
        new_user_entity = UserEntity(
            username=new_user.username,
            email=new_user.email,
            hashed_password=hashed_password,
            is_active=new_user.is_active,
            is_staff=new_user.is_staff,
            is_superuser=new_user.is_superuser,
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

    def execute(self, user_id: int, attrs: UserChanges) -> UserEntity | None:
        """
        Updates a user with the provided data.
        Only non-None fields are updated.
        """
        existing_user = self.user_repo.get_by_id(user_id)
        if not existing_user:
            return None

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
