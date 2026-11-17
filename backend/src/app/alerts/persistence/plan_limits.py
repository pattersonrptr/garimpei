"""AlertLimitsReader over billing's plan limits."""

from src.app.alerts.entities import AlertLimits
from src.app.alerts.ports import AlertLimitsReader
from src.app.billing.use_cases import GetUserPlanLimitsUseCase


class BillingAlertLimits(AlertLimitsReader):
    def __init__(self, plan_limits: GetUserPlanLimitsUseCase):
        self.plan_limits = plan_limits

    def for_user(self, user_id: int) -> AlertLimits:
        limits = self.plan_limits.execute(user_id)
        return AlertLimits(
            plan_name=limits.plan_name,
            max_active_alerts=limits.max_active_alerts,
            min_frequency_minutes=limits.min_frequency_minutes,
            max_sources=limits.max_sources,
        )
