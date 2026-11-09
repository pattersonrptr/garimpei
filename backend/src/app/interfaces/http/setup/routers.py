"""Router registration and setup."""

from fastapi import FastAPI

from src.app.interfaces.http.controllers import (
    admin_controller,
    auth_controller,
    dashboard_controller,
    notification_log_controller,
    offer_controller,
    plan_controller,
    price_alert_controller,
    price_history_controller,
    product_controller,
    search_config_controller,
    search_execution_log_controller,
    source_website_controller,
    subscription_controller,
    user_controller,
)


def setup_routers(app: FastAPI) -> None:
    """
    Register all API routers for the application.

    Current routes:
    - /auth: Authentication endpoints (login, token refresh)
    - /users: User management endpoints (CRUD operations)
    - /products: Product tracking endpoints (CRUD operations)
    - /offers: Offer ingestion by ISBN for collectors
    - /source-websites: Source website management endpoints (CRUD operations)
    - /price-histories: Price history tracking endpoints
    - /price-alerts: Price alert management endpoints (CRUD + notify)
    - /notification-logs: Notification log management endpoints
    - /search-configs: Search configuration management
    - /search-execution-logs: Search execution log management

    Args:
        app: FastAPI application instance
    """
    app.include_router(admin_controller)
    app.include_router(auth_controller)
    app.include_router(dashboard_controller)
    app.include_router(plan_controller)
    app.include_router(subscription_controller)
    app.include_router(user_controller)
    app.include_router(product_controller)
    app.include_router(offer_controller)
    app.include_router(source_website_controller)
    app.include_router(price_history_controller)
    app.include_router(price_alert_controller)
    app.include_router(notification_log_controller)
    app.include_router(search_config_controller)
    app.include_router(search_execution_log_controller)
