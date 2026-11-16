"""AlertOwnerReader over accounts' user repository."""

from src.app.accounts.ports import UserRepositoryInterface
from src.app.alerts.entities import AlertOwner
from src.app.alerts.ports import AlertOwnerReader


class UserAccountOwners(AlertOwnerReader):
    def __init__(self, users: UserRepositoryInterface):
        self.users = users

    def get_by_id(self, user_id: int) -> AlertOwner | None:
        user = self.users.get_by_id(user_id)
        if user is None or user.id is None:
            return None
        return AlertOwner(id=user.id, email=user.email)
