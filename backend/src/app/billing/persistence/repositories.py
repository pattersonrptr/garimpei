from dataclasses import asdict, fields
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from src.app.billing.entities import Plan as PlanEntity
from src.app.billing.entities import Subscription as SubscriptionEntity
from src.app.billing.persistence.models import Plan as PlanModel
from src.app.billing.persistence.models import Subscription as SubscriptionModel
from src.app.billing.ports import (
    PlanRepositoryInterface,
    SubscriptionRepositoryInterface,
)


def _plan_to_entity(row: PlanModel) -> PlanEntity:
    return PlanEntity(**{f.name: getattr(row, f.name) for f in fields(PlanEntity)})


def _plan_columns(plan: PlanEntity) -> dict:
    columns = asdict(plan)
    del columns["id"]
    return columns


class PlanRepository(PlanRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, plan: PlanEntity) -> PlanEntity:
        db_plan = PlanModel(**_plan_columns(plan))
        self.db.add(db_plan)
        self.db.commit()
        self.db.refresh(db_plan)
        return _plan_to_entity(db_plan)

    def get_by_id(self, plan_id: int) -> PlanEntity | None:
        plan = self.db.query(PlanModel).filter(PlanModel.id == plan_id).first()
        if plan:
            return _plan_to_entity(plan)
        return None

    def get_by_name(self, name: str) -> PlanEntity | None:
        plan = self.db.query(PlanModel).filter(PlanModel.name == name).first()
        if plan:
            return _plan_to_entity(plan)
        return None

    def get_all(self) -> list[PlanEntity]:
        plans = (
            self.db.query(PlanModel)
            .filter(PlanModel.is_active.is_(True))
            .order_by(PlanModel.price_cents)
            .all()
        )
        return [_plan_to_entity(p) for p in plans]


def _subscription_to_entity(row: SubscriptionModel) -> SubscriptionEntity:
    return SubscriptionEntity(
        **{f.name: getattr(row, f.name) for f in fields(SubscriptionEntity)}
    )


def _subscription_columns(subscription: SubscriptionEntity) -> dict:
    columns = asdict(subscription)
    del columns["id"]
    return columns


class SubscriptionRepository(SubscriptionRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, subscription: SubscriptionEntity) -> SubscriptionEntity:
        db_sub = SubscriptionModel(**_subscription_columns(subscription))
        self.db.add(db_sub)
        self.db.commit()
        self.db.refresh(db_sub)
        return _subscription_to_entity(db_sub)

    def get_by_user_id(self, user_id: int) -> SubscriptionEntity | None:
        sub = (
            self.db.query(SubscriptionModel)
            .options(joinedload(SubscriptionModel.plan))
            .filter(
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.status == "active",
            )
            .first()
        )
        if sub:
            return _subscription_to_entity(sub)
        return None

    def update(
        self, subscription_id: int, subscription: SubscriptionEntity
    ) -> SubscriptionEntity | None:
        db_sub = (
            self.db.query(SubscriptionModel)
            .filter(SubscriptionModel.id == subscription_id)
            .first()
        )
        if not db_sub:
            return None
        columns = _subscription_columns(subscription)
        columns["updated_at"] = datetime.now(UTC)
        for key, value in columns.items():
            setattr(db_sub, key, value)
        self.db.commit()
        self.db.refresh(db_sub)
        return _subscription_to_entity(db_sub)
