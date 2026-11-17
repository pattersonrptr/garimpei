from dataclasses import asdict, fields

from sqlalchemy.orm import Session

from src.app.billing.entities import Plan as PlanEntity
from src.app.infrastructure.database.models.plan_model import Plan as PlanModel
from src.app.interfaces.repositories.plan_repository import PlanRepositoryInterface


def _to_entity(row: PlanModel) -> PlanEntity:
    return PlanEntity(**{f.name: getattr(row, f.name) for f in fields(PlanEntity)})


def _to_columns(plan: PlanEntity) -> dict:
    columns = asdict(plan)
    del columns["id"]
    return columns


class PlanRepository(PlanRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    def create(self, plan: PlanEntity) -> PlanEntity:
        db_plan = PlanModel(**_to_columns(plan))
        self.db.add(db_plan)
        self.db.commit()
        self.db.refresh(db_plan)
        return _to_entity(db_plan)

    def get_by_id(self, plan_id: int) -> PlanEntity | None:
        plan = self.db.query(PlanModel).filter(PlanModel.id == plan_id).first()
        if plan:
            return _to_entity(plan)
        return None

    def get_by_name(self, name: str) -> PlanEntity | None:
        plan = self.db.query(PlanModel).filter(PlanModel.name == name).first()
        if plan:
            return _to_entity(plan)
        return None

    def get_all(self) -> list[PlanEntity]:
        plans = (
            self.db.query(PlanModel)
            .filter(PlanModel.is_active.is_(True))
            .order_by(PlanModel.price_cents)
            .all()
        )
        return [_to_entity(p) for p in plans]

    def update(self, plan_id: int, plan: PlanEntity) -> PlanEntity | None:
        db_plan = self.db.query(PlanModel).filter(PlanModel.id == plan_id).first()
        if not db_plan:
            return None
        for key, value in _to_columns(plan).items():
            setattr(db_plan, key, value)
        self.db.commit()
        self.db.refresh(db_plan)
        return _to_entity(db_plan)
