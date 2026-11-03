"""Email service port used by the use cases.

Implementations (SendGrid, SMTP) live in
src/app/infrastructure/services/email_service.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailResult:
    """Result of an email send attempt."""

    success: bool
    status_code: int | None = None
    error_message: str | None = None


class EmailServiceInterface(ABC):
    """Abstract interface for email sending."""

    @abstractmethod
    def send_price_alert_email(
        self,
        to_email: str,
        search_term: str,
        product_title: str,
        product_price: float,
        max_price: float,
        product_url: str,
        source_website_name: str,
    ) -> EmailResult:
        """Send a price alert notification email."""
        ...
