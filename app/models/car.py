from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.car_model import CarModel
    from app.models.user import User

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDPK, Base, Created, Updated
from app.models.enums import Condition, FuelType, Transmission


class Car(Base):
    __tablename__ = "cars"
    id: Mapped[UUIDPK]
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    model_id: Mapped[UUID] = mapped_column(ForeignKey("car_models.id", ondelete="RESTRICT"))
    vin: Mapped[str] = mapped_column(String(17), unique=True)
    year: Mapped[int] = mapped_column(SmallInteger)
    mileage_km: Mapped[int] = mapped_column(Integer)
    fuel_type: Mapped[FuelType]
    transmission: Mapped[Transmission]
    condition: Mapped[Condition]
    color: Mapped[str | None] = mapped_column(String(40))
    image_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[Created]
    updated_at: Mapped[Updated]
    model: Mapped["CarModel"] = relationship(lazy="raise")
    owner: Mapped["User"] = relationship(lazy="raise")
    __table_args__ = (
        CheckConstraint("year BETWEEN 1900 AND 2100", name="year_range"),
        CheckConstraint("mileage_km >= 0", name="mileage_nonnegative"),
        CheckConstraint("vin ~ '^[A-HJ-NPR-Z0-9]{17}$'", name="vin_format"),
        Index("ix_cars_model_year_mileage", "model_id", "year", "mileage_km", "id"),
        Index("ix_cars_fuel_year", "fuel_type", "year", "id"),
        Index("ix_cars_owner_created", owner_id, text("created_at DESC"), text("id DESC")),
    )
