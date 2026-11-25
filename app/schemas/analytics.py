from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.models.enums import ListingType
from app.schemas.common import DecimalValue, Schema


class MarketSnapshotRead(Schema):
    id: UUID
    model_id: UUID
    listing_type: ListingType
    as_of: datetime
    window_start: date
    window_end: date
    listing_count: int
    sample_count: int
    median_price_amd: DecimalValue | None
    p25_price_amd: DecimalValue | None
    p75_price_amd: DecimalValue | None
    sale_market_multiplier: DecimalValue | None
    residual_log_mad: DecimalValue | None
    baseline_version: str | None
    occupied_car_days: int | None
    available_car_days: int | None
    occupancy_ratio: DecimalValue | None


class InventorySummary(Schema):
    period_start: date
    period_end: date
    active_sale_listing_count: int
    active_rental_listing_count: int
    confirmed_booking_count: int
    booked_value_amd: DecimalValue
    currency: Literal["AMD"] = "AMD"
