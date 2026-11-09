"""
HTTP Controllers (Adapters for HTTP requests/responses).
"""

from src.app.alerts.http.notification_log_controller import (
    router as notification_log_controller,
)
from src.app.alerts.http.price_alert_controller import (
    router as price_alert_controller,
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
from src.app.interfaces.http.controllers.auth_controller import (
    auth_router as auth_controller,
)
from src.app.interfaces.http.controllers.dashboard_controller import (
    router as dashboard_controller,
)
from src.app.interfaces.http.controllers.plan_controller import (
    router as plan_controller,
)
from src.app.interfaces.http.controllers.search_config_controller import (
    router as search_config_controller,
)
from src.app.interfaces.http.controllers.search_execution_log_controller import (
    router as search_execution_log_controller,
)
from src.app.interfaces.http.controllers.source_website_controller import (
    router as source_website_controller,
)
from src.app.interfaces.http.controllers.subscription_controller import (
    router as subscription_controller,
)
from src.app.interfaces.http.controllers.user_controller import (
    router as user_controller,
)

__all__ = [
    "user_controller",
    "auth_controller",
    "dashboard_controller",
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
