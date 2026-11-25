import math
from decimal import Decimal

from app.pricing_engine.depreciation import sale_factors
from app.pricing_engine.parameters import SALE_VERSION
from app.pricing_engine.types import factor, money


def estimate_sale(
    *,
    baseline: Decimal,
    year: int,
    mileage_km: int,
    condition: str,
    current_year: int,
    market_multiplier=Decimal(1),
    sample_count=0,
    residual_log_mad=Decimal(0),
    usable_statistics=False,
) -> dict:
    factors = sale_factors(year, mileage_km, condition, current_year)
    usable = usable_statistics and sample_count >= 5
    market = market_multiplier if usable else Decimal(1)
    uncertainty = (
        factor(max(0.10, min(0.35, 1.4826 * float(residual_log_mad) + 0.20 / math.sqrt(sample_count + 1))))
        if usable
        else Decimal(".35")
    )
    raw = baseline * factors.age * factors.mileage * factors.condition * market
    return {
        "min_price": money(raw * (1 - uncertainty)),
        "recommended_price": money(raw),
        "max_price": money(raw * (1 + uncertainty)),
        "algorithm_version": SALE_VERSION,
        "factors": {
            "baseline_price_amd": baseline,
            "age_multiplier": factors.age,
            "mileage_multiplier": factors.mileage,
            "condition_multiplier": factors.condition,
            "market_multiplier": market,
            "uncertainty_fraction": uncertainty,
        },
    }
