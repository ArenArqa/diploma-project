from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.core import clock
from app.models.enums import Condition, FuelType, Transmission
from app.schemas.common import Patch, Schema
from app.schemas.reference import BrandRead, ModelRead


class CarCreate(Schema):
    model_id: UUID
    vin: str = Field(pattern=r"^[A-HJ-NPR-Z0-9]{17}$")
    year: int = Field(ge=1900, le=2100)
    mileage_km: int = Field(ge=0, le=2147483647)
    fuel_type: FuelType
    transmission: Transmission
    condition: Condition
    color: str | None = Field(default=None, max_length=40)

    @field_validator("year")
    @classmethod
    def valid_year(cls, value):
        if value > clock.today().year + 1:
            raise ValueError("Year cannot exceed the current business year plus one")
        return value


class CarUpdate(Patch):
    mileage_km: int | None = Field(default=None, ge=0, le=2147483647)
    fuel_type: FuelType | None = None
    transmission: Transmission | None = None
    condition: Condition | None = None
    color: str | None = Field(default=None, max_length=40)


class CarPublicRead(Schema):
    id: UUID
    brand: BrandRead
    model: ModelRead
    year: int
    mileage_km: int
    fuel_type: FuelType
    transmission: Transmission
    condition: Condition
    color: str | None
    image_url: str | None = None


class CarPrivateRead(CarPublicRead):
    owner_id: UUID
    vin: str
    created_at: datetime
    updated_at: datetime
