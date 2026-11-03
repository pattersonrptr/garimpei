"""
Email notification services.

The use cases depend only on ``EmailServiceInterface`` (an interface in
src/app/interfaces/services/email_service.py). Two implementations:

- ``SendGridEmailService``: SendGrid HTTP API (production).
- ``SmtpEmailService``: plain SMTP. In development it points at Mailpit, a
  local inbox (http://localhost:8026 by default) that catches every message, so the
  whole alert -> email flow can be seen without an external account.

``get_email_service()`` picks one from the ``EMAIL_BACKEND`` setting.
"""

import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail, To

from src.app.infrastructure.services.price_alert_email import (
    PriceAlertEmail,
    build_price_alert_email,
)
from src.app.interfaces.services.email_service import (
    EmailResult,
    EmailServiceInterface,
)
from src.config import settings
from src.config.logging_config import get_logger

logger = get_logger(__name__)


def _build_email(
    search_term: str,
    product_title: str,
    product_price: float,
    max_price: float,
    product_url: str,
    source_website_name: str,
) -> PriceAlertEmail:
    return build_price_alert_email(
        search_term=search_term,
        product_title=product_title,
        product_price=product_price,
        max_price=max_price,
        product_url=product_url,
        source_website_name=source_website_name,
        rate_limit_minutes=settings.NOTIFICATION_RATE_LIMIT_MINUTES,
    )


class SendGridEmailService(EmailServiceInterface):
    """SendGrid implementation of the email service."""

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        self.api_key = api_key or settings.SENDGRID_API_KEY
        self.from_email = from_email or settings.FROM_EMAIL
        self.from_name = from_name or settings.NOTIFICATION_FROM_NAME

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
        """Send a price alert notification email via SendGrid."""
        if not self.api_key:
            logger.warning("SendGrid API key not configured, skipping email send")
            return EmailResult(
                success=False,
                error_message="SendGrid API key not configured",
            )

        email = _build_email(
            search_term,
            product_title,
            product_price,
            max_price,
            product_url,
            source_website_name,
        )
        message = Mail(
            from_email=Email(self.from_email, self.from_name),
            to_emails=To(to_email),
            subject=email.subject,
            html_content=Content("text/html", email.html),
        )

        try:
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)

            logger.info(
                "Email sent to %s for alert '%s' (status=%s)",
                to_email,
                search_term,
                response.status_code,
            )
            return EmailResult(
                success=response.status_code in (200, 201, 202),
                status_code=response.status_code,
            )
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e))
            return EmailResult(success=False, error_message=str(e))


class SmtpEmailService(EmailServiceInterface):
    """SMTP implementation (Mailpit in development, any SMTP relay otherwise)."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.username = username if username is not None else settings.SMTP_USERNAME
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.from_email = from_email or settings.FROM_EMAIL
        self.from_name = from_name or settings.NOTIFICATION_FROM_NAME

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
        """Send a price alert notification email over SMTP."""
        if not self.host:
            logger.warning("SMTP host not configured, skipping email send")
            return EmailResult(success=False, error_message="SMTP host not configured")

        email = _build_email(
            search_term,
            product_title,
            product_price,
            max_price,
            product_url,
            source_website_name,
        )
        message = EmailMessage()
        message["Subject"] = email.subject
        message["From"] = formataddr((self.from_name, self.from_email))
        message["To"] = to_email
        message.set_content(email.text)
        message.add_alternative(email.html, subtype="html")

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.send_message(message)

            logger.info(
                "Email sent to %s for alert '%s' via SMTP %s:%s",
                to_email,
                search_term,
                self.host,
                self.port,
            )
            return EmailResult(success=True, status_code=250)
        except (smtplib.SMTPException, OSError) as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e))
            return EmailResult(success=False, error_message=str(e))


def get_email_service() -> EmailServiceInterface:
    """Build the email service selected by the EMAIL_BACKEND setting."""
    backend = settings.EMAIL_BACKEND
    if backend == "smtp":
        return SmtpEmailService()
    if backend == "sendgrid":
        return SendGridEmailService()
    raise ValueError(f"Unknown EMAIL_BACKEND {backend!r}; use 'sendgrid' or 'smtp'")
