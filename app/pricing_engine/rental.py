from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.pricing_engine.parameters import RENTAL_VERSION, SEASONS
from app.pricing_engine.types import factor, money


def duration_factor(day_number: int) -> Decimal:
    return Decimal(1) if day_number <= 6 else Decimal(".90") if day_number <= 29 else Decimal(".80")


def price_rental(base: Decimal, start: date, end: date, occupancy: Decimal | None = None) -> dict:
    days = (end - start).days + 1
    if not 1 <= days <= 90 or base <= 0:
        raise ValueError("Positive base rate and 1–90 inclusive days required")
    demand = (
        Decimal(1)
        if occupancy is None
        else factor(max(Decimal(".85"), min(Decimal("1.35"), Decimal(".85") + Decimal(".50") * occupancy)))
    )
    breakdown = []
    for index in range(days):
        day = start + timedelta(days=index)
        season, duration = Decimal(SEASONS[day.month]), duration_factor(index + 1)
        breakdown.append(
            {
                "date": day.isoformat(),
                "season_multiplier": str(season),
                "duration_multiplier": str(duration),
                "daily_price_amd": str(money(base * season * duration * demand)),
            }
        )
    total = sum((Decimal(d["daily_price_amd"]) for d in breakdown), Decimal(0))
    return {
        "demand_multiplier": str(demand),
        "daily_breakdown": breakdown,
        "effective_daily_rate_amd": str((total / days).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)),
        "total_price_amd": str(total),
        "pricing_version": RENTAL_VERSION,
    }
