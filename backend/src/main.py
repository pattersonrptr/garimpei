"""
Product Tracker API - Main Application Entry Point

FastAPI application for tracking product prices across multiple e-commerce platforms.
Features web scraping, price history tracking, and automated monitoring via Celery tasks.

Architecture: Clean Architecture with Domain-Driven Design
- Domain: Business entities and validation logic
- Use Cases: Application business rules
- Infrastructure: External services (database, scrapers)
- Interfaces: HTTP controllers and API endpoints
"""

# ============================================================================
# STANDARD LIBRARY IMPORTS
# ============================================================================
import os

# ============================================================================
# THIRD-PARTY IMPORTS
# ============================================================================
from fastapi import FastAPI

from src.app.composition import compose
from src.app.infrastructure.database import (
    models,  # noqa: F401 - Ensure models are loaded
)
from src.app.interfaces.http.setup.exception_handlers import setup_exception_handlers
from src.app.interfaces.http.setup.middleware import setup_middleware
from src.app.interfaces.http.setup.routers import setup_routers
from src.config import settings

# ============================================================================
# APPLICATION IMPORTS
# ============================================================================
from src.config.logging_config import get_logger, setup_logging

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
# Initialize logging FIRST (before any other imports that might log)
setup_logging(
    app_name="product-tracker",
    log_level=settings.LOG_LEVEL,
    enable_console=True,
    enable_file=os.getenv("ENABLE_FILE_LOGGING", "true").lower() != "false",
    json_logs=settings.ENABLE_JSON_LOGS,
)

logger = get_logger(__name__)
logger.info(f"Starting Product Tracker API in {settings.ENVIRONMENT} mode")

# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================
app = FastAPI(
    title="Product Tracker API",
    description="REST API for tracking product prices across e-commerce platforms",
    version="1.0.0",
)

# ============================================================================
# MIDDLEWARE SETUP
# ============================================================================
# Register middleware in correct order (see setup/middleware.py for execution order)
setup_middleware(app)

# ============================================================================
# ROUTER REGISTRATION
# ============================================================================
# Register all API endpoints, after connecting modules through their ports
compose()
setup_routers(app)

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================
# Register global exception handlers for JSON:API compliance
setup_exception_handlers(app)
