from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import model_validator

from app.schemas.common import DecimalValue, Schema


class RentalQuoteCreate(Schema):
    listing_id: UUID
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def valid_order(self):
        if self.end_date < self.start_date or (self.end_date - self.start_date).days >= 90:
            raise ValueError("Rental duration must be 1–90 inclusive days")
        return self


class DailyPrice(Schema):
    date: date
    season_multiplier: DecimalValue
    duration_multiplier: DecimalValue
    daily_price_amd: DecimalValue


class RentalQuoteRead(Schema):
    id: UUID
    listing_id: UUID
    car_id: UUID
    start_date: date
    end_date: date
    days: int
    base_daily_rate_amd: DecimalValue
    total_price_amd: DecimalValue
    effective_daily_rate_amd: DecimalValue
    currency: Literal["AMD"] = "AMD"
    demand_multiplier: DecimalValue
    snapshot_status: Literal["fresh", "stale", "missing"]
    market_snapshot_id: UUID | None
    daily_breakdown: list[DailyPrice]
    pricing_version: str
    created_at: datetime
    expires_at: datetime
    accepted_booking_id: UUID | None = None
