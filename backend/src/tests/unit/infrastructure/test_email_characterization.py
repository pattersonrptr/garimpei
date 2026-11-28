"""Characterization tests before the e-mail code moves (Nov 28, 2026).

They pin what the SendGrid and SMTP services and alerts' mailer adapter do
today, so the refactor that gives the alert e-mail its home can prove it
changed nothing. Each test kills a mutation that survived the existing suite.
"""

from typing import Any
from unittest.mock import MagicMock, patch

from src.app.alerts.persistence.mailer import EmailServiceMailer
from src.app.infrastructure.services import email_service as email_module
from src.app.infrastructure.services.email_service import (
    SendGridEmailService,
    SmtpEmailService,
)
from src.app.interfaces.services.email_service import EmailResult

ALERT: dict[str, Any] = {
    "to_email": "user@example.com",
    "search_term": "arquitetura limpa",
    "product_title": "Arquitetura Limpa | Robert C. Martin",
    "product_price": 38.0,
    "max_price": 60.0,
    "product_url": "https://www.example.com/livro/arquitetura-limpa",
    "source_website_name": "enjoei",
}
SUBJECT = "Baixou: arquitetura limpa por R$ 38,00 na Enjoei"


def sendgrid(**overrides) -> SendGridEmailService:
    return SendGridEmailService(
        **{
            "api_key": "SG.key",
            "from_email": "alertas@garimpei.test",
            "from_name": "Garimpei",
            **overrides,
        }
    )


def send_with_sendgrid(status_code=202, side_effect=None, service=None):
    """Send through SendGrid with its client mocked; returns (result, mail)."""
    with patch.object(email_module, "SendGridAPIClient") as client_cls:
        client = client_cls.return_value
        client.send.return_value = MagicMock(status_code=status_code)
        client.send.side_effect = side_effect
        result = (service or sendgrid()).send_price_alert_email(**ALERT)
    mail = client.send.call_args.args[0] if client.send.called else None
    return result, mail, client_cls


class TestSendGridEmailService:
    def test_without_an_api_key_nothing_is_sent(self):
        with patch.object(email_module.settings, "SENDGRID_API_KEY", ""):
            result, mail, client_cls = send_with_sendgrid(
                service=SendGridEmailService(api_key="")
            )

        assert result == EmailResult(
            success=False, error_message="SendGrid API key not configured"
        )
        client_cls.assert_not_called()

    def test_an_accepted_send_is_a_success_with_its_status(self):
        result, _, client_cls = send_with_sendgrid(status_code=202)

        assert result == EmailResult(success=True, status_code=202)
        client_cls.assert_called_once_with("SG.key")

    def test_a_refused_send_is_a_failure_with_its_status(self):
        result, _, _ = send_with_sendgrid(status_code=400)

        assert result == EmailResult(success=False, status_code=400)

    def test_an_error_while_sending_is_a_failure_with_its_message(self):
        result, _, _ = send_with_sendgrid(side_effect=RuntimeError("network down"))

        assert result == EmailResult(success=False, error_message="network down")

    def test_the_mail_goes_to_the_owner_from_the_sender_as_html(self):
        _, mail, _ = send_with_sendgrid()
        body = mail.get()

        assert body["from"] == {"email": "alertas@garimpei.test", "name": "Garimpei"}
        assert body["personalizations"][0]["to"] == [{"email": "user@example.com"}]
        assert body["subject"] == SUBJECT
        [content] = body["content"]
        assert content["type"] == "text/html"
        assert "<html" in content["value"].lower()


class TestSmtpEmailService:
    def send(self) -> tuple[EmailResult, Any]:
        smtp = MagicMock()
        with patch.object(email_module.smtplib, "SMTP") as smtp_cls:
            smtp_cls.return_value.__enter__.return_value = smtp
            result = SmtpEmailService(
                host="mailpit",
                port=1025,
                username="",
                password="",
                use_tls=False,
                from_email="alertas@garimpei.test",
                from_name="Garimpei",
            ).send_price_alert_email(**ALERT)
        return result, smtp.send_message.call_args.args[0]

    def test_a_sent_message_is_a_success_with_status_250(self):
        result, _ = self.send()

        assert result == EmailResult(success=True, status_code=250)

    def test_the_message_comes_from_the_named_sender(self):
        _, message = self.send()

        assert message["From"] == "Garimpei <alertas@garimpei.test>"

    def test_the_plain_text_part_has_no_html(self):
        _, message = self.send()
        text, html = message.iter_parts()

        assert "<" not in text.get_content()
        assert ALERT["product_url"] in text.get_content()
        assert "<html" in html.get_content().lower()


class TestContentSettings:
    def test_the_rate_limit_in_the_mail_comes_from_the_settings(self):
        with patch.object(email_module.settings, "NOTIFICATION_RATE_LIMIT_MINUTES", 45):
            _, mail, _ = send_with_sendgrid()

        assert "a cada 45 minutos" in mail.get()["content"][0]["value"]


class TestAlertsMailerAdapter:
    def test_passes_the_failure_and_its_message_on(self):
        service = MagicMock()
        service.send_price_alert_email.return_value = EmailResult(
            success=False, error_message="smtp down"
        )

        result = EmailServiceMailer(service).send_price_alert_email(**ALERT)

        assert result.success is False
        assert result.error_message == "smtp down"
        service.send_price_alert_email.assert_called_once_with(**ALERT)
