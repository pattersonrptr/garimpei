"""The words of an alert notification: price format, store name, subject."""

import pytest

from src.app.alerts.notification_text import alert_subject, brl, store_name


class TestBrl:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (17.46, "R$ 17,46"),
            (0, "R$ 0,00"),
            (1234.5, "R$ 1.234,50"),
            (1234567.891, "R$ 1.234.567,89"),
        ],
    )
    def test_brazilian_format(self, value, expected):
        assert brl(value) == expected


class TestStoreName:
    def test_known_store(self):
        assert store_name("estante_virtual") == "Estante Virtual"
        assert store_name("olx") == "OLX"

    def test_unknown_store_is_title_cased(self):
        assert store_name("nova_livraria") == "Nova Livraria"


class TestAlertSubject:
    def test_names_the_product_price_and_store(self):
        assert (
            alert_subject("A Divina Comédia", 17.46, "estante_virtual")
            == "Baixou: A Divina Comédia por R$ 17,46 na Estante Virtual"
        )
