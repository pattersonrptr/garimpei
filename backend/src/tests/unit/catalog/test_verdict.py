"""The price verdict rule and the use case that applies it to a book."""

from datetime import UTC, date, datetime, timedelta

import pytest

from src.app.catalog.entities import (
    BookDetail,
    DailyLow,
    ProductCondition,
    PublicOffer,
    VerdictStatus,
)
from src.app.catalog.ports import BookCatalogReader
from src.app.catalog.use_cases import JudgeBookPricesUseCase
from src.app.catalog.verdict import MIN_DAYS, judge_price, without_outliers

USED = ProductCondition.USED
NEW = ProductCondition.NEW
NOW = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)

# 20 days between R$ 30 and R$ 49: p25 = 34.75, p75 = 44.25
HISTORY = [30.0 + i for i in range(20)]


class TestWithoutOutliers:
    def test_drops_a_price_far_above_the_rest(self):
        prices = [40, 42, 41, 39, 43, 750]

        assert without_outliers(prices) == [40, 42, 41, 39, 43]

    def test_drops_a_price_far_below_the_rest(self):
        prices = [40, 42, 41, 39, 43, 2]

        assert 2 not in without_outliers(prices)

    def test_keeps_everything_with_fewer_than_four_prices(self):
        assert without_outliers([10, 500, 20]) == [10, 500, 20]


class TestJudgePrice:
    def test_a_price_at_or_below_the_25th_percentile_is_good(self):
        verdict = judge_price(USED, 34.75, HISTORY)

        assert verdict.status == VerdictStatus.GOOD
        assert verdict.p25 == pytest.approx(34.75)
        assert verdict.low == 30.0
        assert verdict.high == 49.0
        assert verdict.days == 20

    def test_a_price_at_or_above_the_75th_percentile_is_high(self):
        assert judge_price(USED, 44.25, HISTORY).status == VerdictStatus.HIGH

    def test_a_price_in_between_is_normal(self):
        assert judge_price(USED, 40.0, HISTORY).status == VerdictStatus.NORMAL

    def test_needs_the_minimum_days_of_history(self):
        short = HISTORY[: MIN_DAYS - 1]

        assert judge_price(USED, 30.0, short).status == VerdictStatus.LEARNING
        assert judge_price(USED, 30.0, HISTORY[:MIN_DAYS]).status == VerdictStatus.GOOD

    def test_learning_still_reports_the_range_seen(self):
        verdict = judge_price(USED, 31.0, [30.0, 32.0])

        assert verdict.status == VerdictStatus.LEARNING
        assert (verdict.low, verdict.high, verdict.days) == (30.0, 32.0, 2)

    def test_an_outlier_day_does_not_make_a_normal_price_look_good(self):
        # one day a "new" copy listed at R$ 750 was the only offer
        verdict = judge_price(NEW, 44.0, HISTORY + [750.0])

        assert verdict.high == 49.0
        assert verdict.days == 20
        assert verdict.status == VerdictStatus.NORMAL

    def test_nothing_in_stock_has_no_verdict(self):
        verdict = judge_price(USED, None, HISTORY)

        assert verdict.status == VerdictStatus.NO_OFFER
        assert verdict.p25 is not None

    def test_no_history_at_all(self):
        verdict = judge_price(USED, 20.0, [])

        assert verdict.status == VerdictStatus.LEARNING
        assert verdict.days == 0
        assert verdict.low is None


def offer(condition, price, available=True):
    return PublicOffer(
        store="estante_virtual",
        url=f"https://ev/{condition}/{price}",
        condition=condition,
        price=price,
        is_available=available,
        last_checked_at=NOW,
    )


class FakeCatalog(BookCatalogReader):
    def __init__(self, lows):
        self.lows = lows
        self.since = None

    def search(self, term, limit, offset):
        return [], 0

    def get_book(self, isbn13):
        return None

    def daily_lows(self, isbn13, since):
        self.since = since
        return self.lows


class TestJudgeBookPrices:
    def test_judges_new_and_used_against_their_own_history(self):
        start = date(2026, 10, 1)
        lows = [
            DailyLow(day=start + timedelta(days=i), condition=USED, price=p)
            for i, p in enumerate(HISTORY)
        ] + [
            DailyLow(day=start + timedelta(days=i), condition=NEW, price=80.0 + i)
            for i in range(20)
        ]
        book = BookDetail(
            isbn13="9788535914849",
            title="1984",
            offers=(
                offer(USED, 31.0),
                offer(USED, 10.0, available=False),  # sold out: does not count
                offer(NEW, 99.0),
            ),
        )
        catalog = FakeCatalog(lows)

        verdicts = JudgeBookPricesUseCase(catalog, now=lambda: NOW).execute(book)

        by_condition = {v.condition: v for v in verdicts}
        assert by_condition[USED].status == VerdictStatus.GOOD
        assert by_condition[USED].current == 31.0
        assert by_condition[NEW].status == VerdictStatus.HIGH
        assert catalog.since == NOW - timedelta(days=90)
