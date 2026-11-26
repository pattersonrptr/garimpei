"""AlertOwnerReader over accounts' user lookup."""

from src.app.accounts.use_cases import GetUserByIdUseCase
from src.app.alerts.entities import AlertOwner
from src.app.alerts.ports import AlertOwnerReader


class UserAccountOwners(AlertOwnerReader):
    def __init__(self, user_by_id: GetUserByIdUseCase):
        self.user_by_id = user_by_id

    def get_by_id(self, user_id: int) -> AlertOwner | None:
        user = self.user_by_id.execute(user_id)
        if user is None or user.id is None:
            return None
        return AlertOwner(id=user.id, email=user.email, is_active=user.is_active)
