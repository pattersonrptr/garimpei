"""RunLimitsReader over billing's plan limits."""

from src.app.billing.use_cases import GetUserPlanLimitsUseCase
from src.app.searches.entities import RunLimits
from src.app.searches.ports import RunLimitsReader


class RunLimitsOverBilling(RunLimitsReader):
    def __init__(self, plan_limits: GetUserPlanLimitsUseCase):
        self.plan_limits = plan_limits

    def for_user(self, user_id: int) -> RunLimits:
        limits = self.plan_limits.execute(user_id)
        return RunLimits(
            plan_name=limits.plan_name,
            min_frequency_minutes=limits.min_frequency_minutes,
            max_sources=limits.max_sources,
        )
