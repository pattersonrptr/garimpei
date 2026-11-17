from abc import ABC, abstractmethod

from src.app.billing.entities import Plan as PlanEntity
from src.app.billing.entities import Subscription as SubscriptionEntity


class PlanRepositoryInterface(ABC):
    @abstractmethod
    def create(self, plan: PlanEntity) -> PlanEntity:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, plan_id: int) -> PlanEntity | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_name(self, name: str) -> PlanEntity | None:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[PlanEntity]:
        raise NotImplementedError


class SubscriptionRepositoryInterface(ABC):
    @abstractmethod
    def create(self, subscription: SubscriptionEntity) -> SubscriptionEntity:
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> SubscriptionEntity | None:
        raise NotImplementedError

    @abstractmethod
    def update(
        self, subscription_id: int, subscription: SubscriptionEntity
    ) -> SubscriptionEntity | None:
        raise NotImplementedError
