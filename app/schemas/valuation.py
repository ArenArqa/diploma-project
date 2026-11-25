from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.core import clock
from app.models.enums import Condition
from app.schemas.common import DecimalValue, Schema


class SaleValuationRequest(Schema):
    model_id: UUID
    year: int = Field(ge=1900, le=2100)
    mileage_km: int = Field(ge=0, le=2147483647)
    condition: Condition

    @field_validator("year")
    @classmethod
    def valid_year(cls, value):
        if value > clock.today().year + 1:
            raise ValueError("Year is too far in the future")
        return value


class ValuationFactors(Schema):
    baseline_price_amd: DecimalValue
    age_multiplier: DecimalValue
    mileage_multiplier: DecimalValue
    condition_multiplier: DecimalValue
    market_multiplier: DecimalValue
    uncertainty_fraction: DecimalValue


class SaleValuationRead(Schema):
    min_price: DecimalValue
    recommended_price: DecimalValue
    max_price: DecimalValue
    currency: Literal["AMD"] = "AMD"
    range_kind: Literal["heuristic"] = "heuristic"
    factors: ValuationFactors
    comparable_count: int
    snapshot_status: Literal["fresh", "stale", "missing"]
    market_snapshot_id: UUID | None
    algorithm_version: str
    baseline_version: str
