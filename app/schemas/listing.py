from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.models.enums import FuelType, ListingStatus, ListingType, Role
from app.schemas.car import CarPublicRead
from app.schemas.common import DecimalValue, Money, OffsetQuery, Patch, Schema


class ListingCreate(Schema):
    car_id: UUID
    listing_type: ListingType
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=5000)
    city: str = Field(min_length=1, max_length=100)
    price_amd: Money


class ListingUpdate(Patch):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=5000)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    price_amd: Money | None = None
    status: ListingStatus | None = None


class OwnerRead(Schema):
    id: UUID
    full_name: str
    role: Role


class ListingRead(Schema):
    id: UUID
    listing_type: ListingType
    status: ListingStatus
    title: str
    description: str
    city: str
    price_amd: DecimalValue
    currency: Literal["AMD"] = "AMD"
    car: CarPublicRead
    owner: OwnerRead
    created_at: datetime
    updated_at: datetime


class PriceHistoryRead(Schema):
    id: UUID
    old_price_amd: DecimalValue | None
    new_price_amd: DecimalValue
    reason: str
    changed_at: datetime


class ListingSearchQuery(OffsetQuery):
    brand_id: UUID | None = None
    model_id: UUID | None = None
    year_min: int | None = Field(default=None, ge=1900, le=2100)
    year_max: int | None = Field(default=None, ge=1900, le=2100)
    price_min: Money | None = None
    price_max: Money | None = None
    mileage_max: int | None = Field(default=None, ge=0, le=2147483647)
    fuel_type: FuelType | None = None
    listing_type: ListingType | None = None
    sort: Literal["newest", "price_asc", "price_desc", "year_desc", "mileage_asc"] = "newest"
    pagination: Literal["offset", "cursor"] = "offset"
    cursor: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_search(self):
        for lower, upper in [(self.year_min, self.year_max), (self.price_min, self.price_max)]:
            if lower is not None and upper is not None and lower > upper:
                raise ValueError("Minimum must not exceed maximum")
        if self.sort.startswith("price") and self.listing_type is None:
            raise ValueError("Price ordering requires listing_type")
        if self.pagination == "offset" and self.cursor:
            raise ValueError("cursor requires cursor pagination")
        if self.pagination == "cursor" and self.offset:
            raise ValueError("offset cannot be combined with cursor pagination")
        return self
