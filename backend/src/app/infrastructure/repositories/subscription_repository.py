from dataclasses import asdict, fields
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from src.app.billing.entities import Subscription as SubscriptionEntity
from src.app.infrastructure.database.models.subscription_model import (
    Subscription as SubscriptionModel,
)
from src.app.interfaces.repositories.subscription_repository import (
    SubscriptionRepositoryInterface,
)


def _to_entity(row: SubscriptionModel) -> SubscriptionEntity:
    return SubscriptionEntity(
        **{f.name: getattr(row, f.name) for f in fields(SubscriptionEntity)}
    )


def _to_columns(subscription: SubscriptionEntity) -> dict:
    columns = asdict(subscription)
    del columns["id"]
    return columns


class SubscriptionRepository(SubscriptionRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, subscription: SubscriptionEntity) -> SubscriptionEntity:
        db_sub = SubscriptionModel(**_to_columns(subscription))
        self.db.add(db_sub)
        self.db.commit()
        self.db.refresh(db_sub)
        return _to_entity(db_sub)

    def get_by_id(self, subscription_id: int) -> SubscriptionEntity | None:
        sub = (
            self.db.query(SubscriptionModel)
            .options(joinedload(SubscriptionModel.plan))
            .filter(SubscriptionModel.id == subscription_id)
            .first()
        )
        if sub:
            return _to_entity(sub)
        return None

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
            return _to_entity(sub)
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
        for key, value in _to_columns(subscription).items():
            setattr(db_sub, key, value)
        db_sub.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(db_sub)
        return _to_entity(db_sub)
