from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


def factor(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal(".00000001"), rounding=ROUND_HALF_UP)


def money(value: Decimal) -> Decimal:
    return max(Decimal(1), value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class SaleFactors:
    age: Decimal
    mileage: Decimal
    condition: Decimal
