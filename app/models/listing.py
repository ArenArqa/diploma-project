from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.car import Car

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDPK, Base, Created, Updated
from app.models.enums import ListingStatus, ListingType


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[UUIDPK]
    car_id: Mapped[UUID] = mapped_column(ForeignKey("cars.id", ondelete="RESTRICT"), index=True)
    listing_type: Mapped[ListingType]
    status: Mapped[ListingStatus] = mapped_column(default=ListingStatus.active, server_default="active")
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(100))
    price_amd: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    price_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[Created]
    updated_at: Mapped[Updated]
    car: Mapped["Car"] = relationship(lazy="raise")
    __table_args__ = (
        UniqueConstraint("id", "car_id", "listing_type", name="uq_listing_identity"),
        CheckConstraint("price_amd > 0", name="price_positive"),
        CheckConstraint("status <> 'sold' OR listing_type = 'sale'", name="sold_only_sale"),
        Index(
            "uq_one_active_listing_per_car", "car_id", unique=True, postgresql_where=text("status = 'active'")
        ),
        Index(
            "ix_listings_type_price",
            "listing_type",
            "price_amd",
            "id",
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "ix_listings_type_created",
            "listing_type",
            text("created_at DESC"),
            text("id DESC"),
            postgresql_where=text("status = 'active'"),
        ),
    )
