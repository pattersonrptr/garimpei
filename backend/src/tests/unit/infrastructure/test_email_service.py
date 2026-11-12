"""Tests for the email services, the provider factory and the email content."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.app.infrastructure.services import email_service as email_module
from src.app.infrastructure.services.email_service import (
    SendGridEmailService,
    SmtpEmailService,
    get_email_service,
)
from src.app.infrastructure.services.price_alert_email import build_price_alert_email

ALERT: dict[str, Any] = {
    "to_email": "user@example.com",
    "search_term": "arquitetura limpa",
    "product_title": "Arquitetura Limpa | Robert C. Martin",
    "product_price": 38.0,
    "max_price": 60.0,
    "product_url": "https://www.example.com/livro/arquitetura-limpa",
    "source_website_name": "enjoei",
}


class TestPriceAlertEmailContent:
    def _build(self, **overrides):
        args = {k: v for k, v in ALERT.items() if k != "to_email"}
        args.update(overrides)
        return build_price_alert_email(rate_limit_minutes=60, **args)

    def test_subject_and_body(self):
        email = self._build()
        assert email.subject == "Baixou: arquitetura limpa por R$ 38,00 na Enjoei"
        assert "Arquitetura Limpa | Robert C. Martin" in email.html
        assert "R$ 22,00 abaixo do seu alvo" in email.html
        assert "Enjoei" in email.html
        assert "enjoei" not in email.html.replace("example.com", "")
        assert "1 e-mail por alerta a cada 60 minutos" in email.html
        assert ALERT["product_url"] in email.text
        assert "R$ 38,00" in email.text

    def test_has_garimpei_identity_not_the_old_app(self):
        html = self._build().html
        assert "Garimpei" in html
        assert "#ffc928" in html  # the site's gold
        assert "#1976d2" not in html  # the old app's blue
        assert "para a busca" not in html

    def test_listing_data_is_html_escaped(self):
        email = self._build(
            product_title='<script>alert("x")</script>',
            product_url='https://x.test/"><img src=x>',
        )
        assert "<script>" not in email.html
        assert "&lt;script&gt;" in email.html
        assert '"><img' not in email.html


class TestSmtpEmailService:
    def test_sends_multipart_message(self):
        smtp = MagicMock()
        with patch.object(email_module.smtplib, "SMTP") as smtp_cls:
            smtp_cls.return_value.__enter__.return_value = smtp
            service = SmtpEmailService(
                host="mailpit", port=1025, username="", password="", use_tls=False
            )
            result = service.send_price_alert_email(**ALERT)

        assert result.success is True
        smtp_cls.assert_called_once_with("mailpit", 1025, timeout=10)
        smtp.starttls.assert_not_called()
        smtp.login.assert_not_called()
        message = smtp.send_message.call_args.args[0]
        assert message["To"] == "user@example.com"
        assert message["Subject"].startswith("Baixou: ")
        assert message.is_multipart()
        types = [part.get_content_type() for part in message.iter_parts()]
        assert types == ["text/plain", "text/html"]

    def test_uses_tls_and_login_when_configured(self):
        smtp = MagicMock()
        with patch.object(email_module.smtplib, "SMTP") as smtp_cls:
            smtp_cls.return_value.__enter__.return_value = smtp
            service = SmtpEmailService(
                host="smtp.test", port=587, username="u", password="p", use_tls=True
            )
            service.send_price_alert_email(**ALERT)

        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("u", "p")

    def test_connection_error_returns_failure(self):
        with patch.object(
            email_module.smtplib, "SMTP", side_effect=OSError("connection refused")
        ):
            result = SmtpEmailService(host="mailpit", port=1025).send_price_alert_email(
                **ALERT
            )
        assert result.success is False
        assert "connection refused" in result.error_message

    def test_missing_host_skips_send(self):
        with patch.object(email_module.settings, "SMTP_HOST", ""):
            result = SmtpEmailService().send_price_alert_email(**ALERT)
        assert result.success is False
        assert result.error_message == "SMTP host not configured"


class TestEmailServiceFactory:
    @pytest.mark.parametrize(
        "backend,expected",
        [("smtp", SmtpEmailService), ("sendgrid", SendGridEmailService)],
    )
    def test_selects_backend(self, backend, expected):
        with patch.object(email_module.settings, "EMAIL_BACKEND", backend):
            assert isinstance(get_email_service(), expected)

    def test_unknown_backend_fails_loudly(self):
        with (
            patch.object(email_module.settings, "EMAIL_BACKEND", "carrier-pigeon"),
            pytest.raises(ValueError, match="EMAIL_BACKEND"),
        ):
            get_email_service()
