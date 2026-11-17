from fastapi import APIRouter, Depends

from src.app.accounts.entities import User as UserEntity
from src.app.accounts.http.auth import get_current_superuser
from src.app.billing import wiring
from src.app.billing.entities import Plan as PlanEntity
from src.app.billing.http.plan_presenter import PlanPresenter
from src.app.billing.http.plan_schema import (
    PlanCreateRequest,
    PlanReadResponse,
    PlansCollectionResponse,
)
from src.app.billing.ports import PlanRepositoryInterface
from src.app.billing.use_cases import (
    CreatePlanUseCase,
    GetPlanUseCase,
    ListPlansUseCase,
    PlanNotFoundError,
)
from src.app.infrastructure.database_config import get_db
from src.config.logging_config import get_logger

router = APIRouter(tags=["plans"], prefix="/plans")

logger = get_logger(__name__)


def get_plan_repository(db=Depends(get_db)) -> PlanRepositoryInterface:
    return wiring.plans(db)


@router.get("/", response_model=PlansCollectionResponse)
def list_plans(
    plan_repo: PlanRepositoryInterface = Depends(get_plan_repository),
):
    """List all active plans. Public endpoint (no auth required)."""
    plans = ListPlansUseCase(plan_repo).execute()
    return PlanPresenter.handle_collection_success(plans)


@router.get("/{plan_id}", response_model=PlanReadResponse)
def get_plan(
    plan_id: int,
    plan_repo: PlanRepositoryInterface = Depends(get_plan_repository),
):
    """Get a single plan by ID. Public endpoint."""
    try:
        plan = GetPlanUseCase(plan_repo).execute(plan_id)
    except PlanNotFoundError:
        return PlanPresenter.handle_not_found(f"id={plan_id}")
    return PlanPresenter.handle_success(plan)


@router.post("/", response_model=PlanReadResponse, status_code=201)
def create_plan(
    plan_in: PlanCreateRequest,
    plan_repo: PlanRepositoryInterface = Depends(get_plan_repository),
    current_user: UserEntity = Depends(get_current_superuser),
):
    """Create a new plan. Superuser only."""
    logger.info(
        f"Creating plan: {plan_in.data.attributes.name}",
        extra={"action": "create_plan", "user_id": current_user.id},
    )
    attrs = plan_in.data.attributes
    created = CreatePlanUseCase(plan_repo).execute(PlanEntity(**attrs.model_dump()))
    return PlanPresenter.handle_success(created)
