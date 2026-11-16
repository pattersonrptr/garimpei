"""Composition root: connects modules through the ports they own.

A module that needs something from another defines a port; the adapter lives
in the other module. Wiring one module's adapter into another module's port
happens here, so neither module imports the other for it.

Every entry point that serves catalog's HTTP layer must call ``compose()``
once before handling requests (``src/main.py`` does; tests use its ``app``).
Without it, catalog's endpoints that need another module's adapter fail
with "No ... registered".
"""

from src.app.alerts.persistence.listing_scope import AlertListingScope
from src.app.alerts.wiring import CatalogAlertChecks
from src.app.catalog.http.listing_scope import use_listing_scope
from src.app.catalog.http.price_alert_checks import use_price_alert_checks


def compose() -> None:
    """Register every cross-module adapter. Called once at start-up."""
    use_listing_scope(AlertListingScope())
    use_price_alert_checks(CatalogAlertChecks)
