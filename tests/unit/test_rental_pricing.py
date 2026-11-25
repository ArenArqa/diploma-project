from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.pricing_engine.rental import price_rental


@pytest.mark.parametrize(
    "days,last_factor", [(1, "1"), (6, "1"), (7, ".90"), (29, ".90"), (30, ".80"), (90, ".80")]
)
def test_progressive_duration(days, last_factor):
    start = date(2026, 3, 1)
    result = price_rental(Decimal(20000), start, start + timedelta(days=days - 1))
    assert Decimal(result["daily_breakdown"][-1]["duration_multiplier"]) == Decimal(last_factor)
    assert len(result["daily_breakdown"]) == days
    assert sum(Decimal(d["daily_price_amd"]) for d in result["daily_breakdown"]) == Decimal(
        result["total_price_amd"]
    )


def test_month_boundary_and_leap_year():
    result = price_rental(Decimal(10000), date(2028, 2, 28), date(2028, 3, 1))
    assert len(result["daily_breakdown"]) == 3
    assert Decimal(result["total_price_amd"]) == 28000


def test_no_price_cliff_at_discount_thresholds():
    start = date(2026, 3, 1)
    totals = [
        Decimal(price_rental(Decimal(20000), start, start + timedelta(days=n - 1))["total_price_amd"])
        for n in range(1, 91)
    ]
    assert all(b > a for a, b in zip(totals, totals[1:]))


@pytest.mark.parametrize(
    "occupancy,expected", [(None, "1"), (Decimal(0), ".85"), (Decimal(".5"), "1.10"), (Decimal(1), "1.35")]
)
def test_demand(occupancy, expected):
    result = price_rental(Decimal(20000), date(2026, 3, 1), date(2026, 3, 1), occupancy)
    assert Decimal(result["demand_multiplier"]) == Decimal(expected)


def test_whole_amd_rounding():
    result = price_rental(Decimal(10001), date(2026, 3, 1), date(2026, 3, 7), Decimal(".333333"))
    assert all(Decimal(d["daily_price_amd"]) % 1 == 0 for d in result["daily_breakdown"])


@pytest.mark.parametrize("duration", [0, 91])
def test_invalid_duration(duration):
    with pytest.raises(ValueError):
        price_rental(Decimal(100), date(2026, 3, 1), date(2026, 3, 1) + timedelta(days=duration - 1))
