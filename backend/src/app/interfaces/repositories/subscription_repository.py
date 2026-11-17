from abc import ABC, abstractmethod

from src.app.billing.entities import Subscription as SubscriptionEntity


class SubscriptionRepositoryInterface(ABC):
    @abstractmethod
    def create(self, subscription: SubscriptionEntity) -> SubscriptionEntity:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, subscription_id: int) -> SubscriptionEntity | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> SubscriptionEntity | None:
        raise NotImplementedError

    @abstractmethod
    def update(
        self, subscription_id: int, subscription: SubscriptionEntity
    ) -> SubscriptionEntity | None:
        raise NotImplementedError
