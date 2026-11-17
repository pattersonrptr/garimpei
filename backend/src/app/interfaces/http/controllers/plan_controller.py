from fastapi import APIRouter, Depends

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import get_current_superuser
from src.app.billing.entities import Plan as PlanEntity
from src.app.infrastructure.database_config import get_db
from src.app.infrastructure.repositories.plan_repository import PlanRepository
from src.app.interfaces.http.presenters.plan_presenter import PlanPresenter
from src.app.interfaces.http.schemas.plan_schema import (
    PlanCreateRequest,
    PlanReadResponse,
    PlansCollectionResponse,
)
from src.config.logging_config import get_logger

router = APIRouter(tags=["plans"], prefix="/plans")

logger = get_logger(__name__)


def get_plan_repository(db=Depends(get_db)) -> PlanRepository:
    return PlanRepository(db)


@router.get("/", response_model=PlansCollectionResponse)
def list_plans(
    plan_repo: PlanRepository = Depends(get_plan_repository),
):
    """List all active plans. Public endpoint (no auth required)."""
    plans = plan_repo.get_all()
    return PlanPresenter.handle_collection_success(plans)


@router.get("/{plan_id}", response_model=PlanReadResponse)
def get_plan(
    plan_id: int,
    plan_repo: PlanRepository = Depends(get_plan_repository),
):
    """Get a single plan by ID. Public endpoint."""
    plan = plan_repo.get_by_id(plan_id)
    if not plan:
        return PlanPresenter.handle_not_found(f"id={plan_id}")
    return PlanPresenter.handle_success(plan)


@router.post("/", response_model=PlanReadResponse, status_code=201)
def create_plan(
    plan_in: PlanCreateRequest,
    plan_repo: PlanRepository = Depends(get_plan_repository),
    current_user: UserEntity = Depends(get_current_superuser),
):
    """Create a new plan. Superuser only."""
    logger.info(
        f"Creating plan: {plan_in.data.attributes.name}",
        extra={"action": "create_plan", "user_id": current_user.id},
    )
    attrs = plan_in.data.attributes
    entity = PlanEntity(**attrs.model_dump())
    created = plan_repo.create(entity)
    return PlanPresenter.handle_success(created)
