"""SearchAlerts over alerts' price alert repository."""

from src.app.alerts.ports import PriceAlertRepositoryInterface
from src.app.searches.ports import SearchAlerts


class SearchAlertsOverAlerts(SearchAlerts):
    def __init__(self, price_alerts: PriceAlertRepositoryInterface):
        self.price_alerts = price_alerts

    def user_has_alert(self, user_id: int, search_id: int) -> bool:
        return any(
            alert.search_config_id == search_id
            for alert in self.price_alerts.get_by_user_id(user_id)
        )

    def count_using(self, search_id: int) -> int:
        return self.price_alerts.count_by_search_config_id(search_id)
