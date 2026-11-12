"""AlertMailer over the older e-mail service (SendGrid or SMTP)."""

from src.app.alerts.entities import MailResult
from src.app.alerts.ports import AlertMailer
from src.app.interfaces.services.email_service import EmailServiceInterface


class EmailServiceMailer(AlertMailer):
    def __init__(self, email_service: EmailServiceInterface):
        self.email_service = email_service

    def send_price_alert_email(
        self,
        to_email: str,
        search_term: str,
        product_title: str,
        product_price: float,
        max_price: float,
        product_url: str,
        source_website_name: str,
    ) -> MailResult:
        result = self.email_service.send_price_alert_email(
            to_email=to_email,
            search_term=search_term,
            product_title=product_title,
            product_price=product_price,
            max_price=max_price,
            product_url=product_url,
            source_website_name=source_website_name,
        )
        return MailResult(success=result.success, error_message=result.error_message)
