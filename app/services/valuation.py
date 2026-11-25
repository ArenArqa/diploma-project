from app.core import clock
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models import CarModel, ValuationBaseline
from app.models.enums import ListingType
from app.pricing_engine.valuation import estimate_sale
from app.repositories.analytics import latest_snapshot
from app.schemas.valuation import SaleValuationRead


def snapshot_status(snapshot):
    if snapshot is None:
        return "missing"
    return (
        "fresh"
        if 0 <= (clock.now() - snapshot.as_of).total_seconds() <= get_settings().statistics_max_age_seconds
        else "stale"
    )


async def value_car(session, data):
    if not await session.get(CarModel, data.model_id):
        raise DomainError(404, "model_not_found", "Model not found.")
    baseline = await session.get(ValuationBaseline, data.model_id)
    if not baseline:
        raise DomainError(422, "valuation_baseline_missing", "No valuation baseline exists for this model.")
    snapshot = await latest_snapshot(session, data.model_id, ListingType.sale)
    status = snapshot_status(snapshot)
    usable = (
        status == "fresh"
        and snapshot.baseline_version == baseline.version
        and snapshot.sale_market_multiplier is not None
    )
    result = estimate_sale(
        baseline=baseline.base_price_amd,
        year=data.year,
        mileage_km=data.mileage_km,
        condition=data.condition,
        current_year=clock.today().year,
        market_multiplier=snapshot.sale_market_multiplier if usable else 1,
        sample_count=snapshot.sample_count if usable else 0,
        residual_log_mad=snapshot.residual_log_mad or 0 if usable else 0,
        usable_statistics=usable,
    )
    return SaleValuationRead(
        **result,
        comparable_count=snapshot.sample_count if usable else 0,
        snapshot_status=status,
        market_snapshot_id=snapshot.id if snapshot else None,
        baseline_version=baseline.version,
    )
