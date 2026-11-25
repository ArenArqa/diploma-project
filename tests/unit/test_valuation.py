from decimal import Decimal

import pytest

from app.pricing_engine.depreciation import sale_factors
from app.pricing_engine.statistics import calibrate
from app.pricing_engine.valuation import estimate_sale


def estimate(**overrides):
    return estimate_sale(
        **{
            "baseline": Decimal(10000000),
            "year": 2020,
            "mileage_km": 75000,
            "condition": "good",
            "current_year": 2026,
            **overrides,
        }
    )


def test_depreciation_boundaries():
    assert sale_factors(2026, 0, "good", 2026).age == 1
    assert sale_factors(2025, 0, "good", 2026).age == Decimal(".85")
    assert sale_factors(1900, 0, "good", 2026).age == Decimal(".12")


def test_age_curve_is_monotonic():
    prices = [estimate(year=2026 - age, mileage_km=0)["recommended_price"] for age in range(100)]
    assert prices == sorted(prices, reverse=True)


def test_only_excess_mileage_penalized():
    assert estimate(mileage_km=0)["recommended_price"] == estimate(mileage_km=90000)["recommended_price"]
    assert estimate(mileage_km=100000)["recommended_price"] < estimate(mileage_km=90000)["recommended_price"]
    assert sale_factors(2020, 2000000000, "good", 2026).mileage == Decimal(".65")


@pytest.mark.parametrize("condition", ["poor", "fair", "good", "excellent"])
def test_ordered_positive_ranges(condition):
    result = estimate(condition=condition)
    assert 0 < result["min_price"] <= result["recommended_price"] <= result["max_price"]


def test_condition_order():
    prices = [estimate(condition=c)["recommended_price"] for c in ["poor", "fair", "good", "excellent"]]
    assert prices == sorted(prices)


def test_small_sample_and_stale_fallback():
    for count, usable in [(4, True), (100, False)]:
        result = estimate(sample_count=count, usable_statistics=usable, market_multiplier=Decimal("1.15"))
        assert result["factors"]["market_multiplier"] == 1
        assert result["factors"]["uncertainty_fraction"] == Decimal(".35")


def test_calibration_shrinks_and_clips_outliers():
    assert calibrate([2] * 4, [0] * 4)[0] == 1
    factor, _ = calibrate([1.1] * 5, [0] * 5)
    assert 1 < factor < Decimal("1.1")
    assert calibrate([100] * 100, [0] * 100)[0] == Decimal("1.15")
    assert calibrate([0.001] * 100, [0] * 100)[0] == Decimal(".85")
