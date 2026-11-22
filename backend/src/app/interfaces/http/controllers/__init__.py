"""
HTTP Controllers (Adapters for HTTP requests/responses).
"""

from src.app.accounts.http.auth_controller import (
    auth_router as auth_controller,
)
from src.app.accounts.http.user_controller import (
    router as user_controller,
)
from src.app.alerts.http.my_alerts_controller import (
    router as my_alerts_controller,
)
from src.app.alerts.http.notification_log_controller import (
    router as notification_log_controller,
)
from src.app.alerts.http.price_alert_controller import (
    router as price_alert_controller,
)
from src.app.billing.http.plan_controller import (
    router as plan_controller,
)
from src.app.billing.http.subscription_controller import (
    router as subscription_controller,
)
from src.app.catalog.http.book_controller import (
    router as book_controller,
)
from src.app.catalog.http.offer_controller import (
    router as offer_controller,
)
from src.app.catalog.http.price_history_controller import (
    router as price_history_controller,
)
from src.app.catalog.http.product_controller import (
    router as product_controller,
)
from src.app.interfaces.http.controllers.admin_controller import (
    router as admin_controller,
)
from src.app.interfaces.http.controllers.dashboard_controller import (
    router as dashboard_controller,
)
from src.app.searches.http.saved_search_controller import (
    router as search_config_controller,
)
from src.app.searches.http.search_run_controller import (
    router as search_execution_log_controller,
)
from src.app.stores.http.store_controller import (
    router as source_website_controller,
)

__all__ = [
    "user_controller",
    "auth_controller",
    "dashboard_controller",
    "book_controller",
    "my_alerts_controller",
    "offer_controller",
    "product_controller",
    "source_website_controller",
    "price_history_controller",
    "price_alert_controller",
    "notification_log_controller",
    "plan_controller",
    "search_config_controller",
    "search_execution_log_controller",
    "subscription_controller",
]
