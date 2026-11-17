from abc import ABC, abstractmethod

from src.app.billing.entities import Plan as PlanEntity


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

    @abstractmethod
    def update(self, plan_id: int, plan: PlanEntity) -> PlanEntity | None:
        raise NotImplementedError
