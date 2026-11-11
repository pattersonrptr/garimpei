"""The price verdict rule: is today's lowest price a good one?

Decided in Phase 4 (docs/plan/phase-4-verdict-alerts.md):

1. Take the book's daily lows of one condition over the window (90 days).
2. Drop outliers with Tukey's fences: below Q1 - 1.5 IQR or above
   Q3 + 1.5 IQR (one store listing a "new" copy at R$ 750 must not make
   every other price look cheap).
3. Fewer than ``MIN_DAYS`` days left: still learning, no verdict.
4. Current lowest price in stock <= 25th percentile: good; >= 75th: high
   (wait); in between: normal.
"""

from collections.abc import Sequence
from statistics import quantiles

from src.app.catalog.entities import PriceVerdict, ProductCondition, VerdictStatus

MIN_DAYS = 14
IQR_FENCE = 1.5


def _quartiles(prices: Sequence[float]) -> tuple[float, float]:
    if len(prices) == 1:
        return prices[0], prices[0]
    q1, _, q3 = quantiles(prices, n=4, method="inclusive")
    return q1, q3


def without_outliers(prices: Sequence[float]) -> list[float]:
    """The prices inside Tukey's fences (all of them when fewer than four)."""
    if len(prices) < 4:
        return list(prices)
    q1, q3 = _quartiles(prices)
    spread = IQR_FENCE * (q3 - q1)
    return [p for p in prices if q1 - spread <= p <= q3 + spread]


def judge_price(
    condition: ProductCondition,
    current: float | None,
    daily_lows: Sequence[float],
    min_days: int = MIN_DAYS,
) -> PriceVerdict:
    """The verdict for ``current`` against one condition's daily lows."""
    kept = without_outliers(daily_lows)
    days = len(kept)
    if not kept:
        stats: dict = {}
    else:
        p25, p75 = _quartiles(kept)
        stats = {"low": min(kept), "high": max(kept), "p25": p25, "p75": p75}

    if current is None:
        status = VerdictStatus.NO_OFFER
    elif days < min_days:
        status = VerdictStatus.LEARNING
    elif current <= stats["p25"]:
        status = VerdictStatus.GOOD
    elif current >= stats["p75"]:
        status = VerdictStatus.HIGH
    else:
        status = VerdictStatus.NORMAL

    return PriceVerdict(
        condition=condition, status=status, current=current, days=days, **stats
    )
