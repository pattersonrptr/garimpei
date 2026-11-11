"""Book alerts: which offers an alert wants, and creation without a SearchConfig."""

from unittest.mock import MagicMock

import pytest

from src.app.alerts.entities import PriceAlert
from src.app.alerts.use_cases import CreatePriceAlertUseCase


def book_alert(condition):
    return PriceAlert(
        search_term="1984",
        max_price=20,
        user_id=1,
        canonical_product_id=7,
        condition=condition,
    )


class TestAcceptsCondition:
    @pytest.mark.parametrize(
        ("wanted", "offer", "accepted"),
        [
            ("used", "used", True),
            ("used", "new", False),
            ("new", "new", True),
            ("any", "used", True),
            ("any", "new", True),
            ("any", "undetermined", False),
            (None, "used", True),
        ],
    )
    def test_matches_the_offer_condition(self, wanted, offer, accepted):
        assert book_alert(wanted).accepts_condition(offer) is accepted

    def test_keyword_alerts_are_not_book_alerts(self):
        assert not PriceAlert(search_term="x", max_price=1).is_book_alert
        assert book_alert("any").is_book_alert


class TestCreateBookAlert:
    def test_a_book_alert_gets_no_search_config(self):
        alerts, configs = MagicMock(), MagicMock()
        alerts.create.side_effect = lambda alert: alert

        created = CreatePriceAlertUseCase(alerts, configs).execute(book_alert("used"))

        assert created.search_config_id is None
        configs.create.assert_not_called()
        configs.get_by_search_term_and_user_id.assert_not_called()
