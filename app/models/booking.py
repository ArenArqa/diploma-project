from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.rental_quote import RentalQuote

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import DATERANGE, ExcludeConstraint, Range
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDPK, Base, Created
from app.models.enums import BookingStatus


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[UUIDPK]
    quote_id: Mapped[UUID] = mapped_column(unique=True)
    car_id: Mapped[UUID] = mapped_column(ForeignKey("cars.id", ondelete="RESTRICT"))
    renter_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    start_date: Mapped[date]
    end_date: Mapped[date]
    period: Mapped[Range[date]] = mapped_column(
        DATERANGE, Computed("daterange(start_date, end_date, '[]')", persisted=True)
    )
    status: Mapped[BookingStatus] = mapped_column(default=BookingStatus.confirmed, server_default="confirmed")
    created_at: Mapped[Created]
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    quote: Mapped["RentalQuote"] = relationship(
        lazy="raise",
        foreign_keys=lambda: [
            Booking.quote_id,
            Booking.car_id,
            Booking.renter_id,
            Booking.start_date,
            Booking.end_date,
        ],
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["quote_id", "car_id", "renter_id", "start_date", "end_date"],
            [
                "rental_quotes.id",
                "rental_quotes.car_id",
                "rental_quotes.renter_id",
                "rental_quotes.start_date",
                "rental_quotes.end_date",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "end_date >= start_date AND end_date - start_date + 1 <= 90", name="booking_dates_valid"
        ),
        CheckConstraint(
            "(status = 'confirmed' AND cancelled_at IS NULL AND cancelled_by IS NULL "
            "AND cancellation_reason IS NULL) OR (status = 'cancelled' AND "
            "cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL)",
            name="cancellation_consistent",
        ),
        ExcludeConstraint(
            (car_id, "="),
            (period, "&&"),
            using="gist",
            where="status = 'confirmed'",
            name="bookings_no_overlap",
        ),
        Index("ix_bookings_renter_created", renter_id, text("created_at DESC"), text("id DESC")),
        Index("ix_bookings_car_status_end", "car_id", "status", "end_date"),
    )
