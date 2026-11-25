from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDPK, Base, Created
from app.models.enums import ListingType


class RentalQuote(Base):
    __tablename__ = "rental_quotes"
    id: Mapped[UUIDPK]
    listing_id: Mapped[UUID]
    car_id: Mapped[UUID]
    listing_type: Mapped[ListingType] = mapped_column(default=ListingType.rent)
    renter_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    start_date: Mapped[date]
    end_date: Mapped[date]
    days: Mapped[int] = mapped_column(SmallInteger, Computed("end_date - start_date + 1", persisted=True))
    base_daily_rate_amd: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    total_price_amd: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    market_snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("market_snapshots.id", ondelete="RESTRICT")
    )
    pricing_version: Mapped[str] = mapped_column(String(32))
    pricing_breakdown: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[Created]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ["listing_id", "car_id", "listing_type"],
            ["listings.id", "listings.car_id", "listings.listing_type"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "id", "car_id", "renter_id", "start_date", "end_date", name="uq_quote_booking_terms"
        ),
        CheckConstraint("listing_type = 'rent'", name="rental_only"),
        CheckConstraint("days BETWEEN 1 AND 90", name="duration_valid"),
        CheckConstraint("base_daily_rate_amd > 0 AND total_price_amd > 0", name="amounts_positive"),
        CheckConstraint("expires_at > created_at", name="expiration_valid"),
        Index("ix_quotes_renter_created", renter_id, text("created_at DESC")),
    )
