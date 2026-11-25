from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.enums import BookingStatus
from app.schemas.common import DecimalValue, Schema
from app.schemas.quote import RentalQuoteRead


class BookingCreate(Schema):
    quote_id: UUID


class BookingCancel(Schema):
    reason: str | None = Field(default=None, max_length=500)


class BookingRead(Schema):
    id: UUID
    quote_id: UUID
    listing_id: UUID
    car_id: UUID
    renter_id: UUID
    start_date: date
    end_date: date
    days: int
    status: BookingStatus
    phase: Literal["upcoming", "in_progress", "completed", "cancelled"]
    total_price_amd: DecimalValue
    currency: Literal["AMD"] = "AMD"
    pricing_breakdown: RentalQuoteRead
    created_at: datetime
    cancelled_at: datetime | None
    cancellation_reason: str | None


class DateInterval(Schema):
    start_date: date
    end_date: date


class AvailabilityRead(Schema):
    listing_id: UUID
    start_date: date
    end_date: date
    blocked_intervals: list[DateInterval]
