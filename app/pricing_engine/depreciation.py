import math

from app.pricing_engine.parameters import CONDITION
from app.pricing_engine.types import SaleFactors, factor


def sale_factors(year: int, mileage_km: int, condition: str, current_year: int) -> SaleFactors:
    age = max(0, current_year - year)
    depreciation = 1 if age == 0 else max(0.12, 0.85 * 0.9 ** (age - 1))
    excess = max(0, mileage_km - 15000 * age)
    mileage = max(0.65, math.exp(-0.035 * excess / 10000))
    return SaleFactors(factor(depreciation), factor(mileage), CONDITION[condition])
