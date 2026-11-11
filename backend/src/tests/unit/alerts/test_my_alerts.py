"""ListMyAlertsUseCase and ProductSnapshot.lowest_for, with fakes."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from src.app.alerts.entities import (
    NoticeHistory,
    OfferPrice,
    PriceAlert,
    ProductSnapshot,
)
from src.app.alerts.use_cases import ListMyAlertsUseCase

T0 = datetime(2026, 11, 11, tzinfo=UTC)


def snapshot(**lowest):
    return ProductSnapshot(
        id=7,
        category="book",
        title="1984",
        lowest={c: OfferPrice(price=p, store="ev") for c, p in lowest.items()},
    )


class TestLowestFor:
    def test_one_condition(self):
        assert snapshot(used=20, new=50).lowest_for("new")[1].price == 50

    def test_any_takes_the_cheapest_condition(self):
        condition, offer = snapshot(used=20, new=50).lowest_for("any")
        assert (condition, offer.price) == ("used", 20)

    def test_none_when_nothing_in_that_condition(self):
        assert snapshot(new=50).lowest_for("used") is None


def alert(id_, active=True, age_days=0, product=7):
    return PriceAlert(
        id=id_,
        search_term="1984",
        max_price=20,
        user_id=1,
        is_active=active,
        canonical_product_id=product,
        condition="used",
        created_at=T0 - timedelta(days=age_days),
    )


class TestListMyAlerts:
    def test_active_first_then_newest_without_keyword_alerts(self):
        alerts = MagicMock()
        alerts.get_by_user_id.return_value = [
            alert(1, age_days=3),
            alert(2, active=False, age_days=0),
            alert(3, age_days=1),
            PriceAlert(id=4, search_term="orwell", max_price=9, user_id=1),
        ]
        products = MagicMock()
        products.snapshots.return_value = {7: snapshot(used=18)}
        notices = MagicMock()
        notices.sent_history.return_value = {3: NoticeHistory(total=2)}

        items = ListMyAlertsUseCase(alerts, products, notices).execute(1)

        assert [i.alert.id for i in items] == [3, 1, 2]
        products.snapshots.assert_called_once_with([7])
        assert items[0].notices.total == 2
        assert items[1].notices == NoticeHistory()
        assert items[0].product.title == "1984"

    def test_no_product_alerts_reads_nothing_else(self):
        alerts = MagicMock()
        alerts.get_by_user_id.return_value = []
        products, notices = MagicMock(), MagicMock()

        assert ListMyAlertsUseCase(alerts, products, notices).execute(1) == []
        products.snapshots.assert_not_called()
