from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.core import clock
from app.core.exceptions import DomainError
from app.models import Booking
from app.models.enums import BookingStatus


async def has_unfinished(session, car_id):
    return bool(
        await session.scalar(
            select(Booking.id)
            .where(
                Booking.car_id == car_id,
                Booking.status == BookingStatus.confirmed,
                Booking.end_date >= clock.today(),
            )
            .limit(1)
        )
    )


async def ensure_available(session, car_id, start, end):
    conflict = await session.scalar(
        select(Booking.id)
        .where(
            Booking.car_id == car_id,
            Booking.status == BookingStatus.confirmed,
            Booking.period.op("&&")(func.daterange(start, end, "[]")),
        )
        .limit(1)
    )
    if conflict:
        raise DomainError(409, "booking_overlap", "This car is already booked for those dates.")


async def get_booking(session, booking_id):
    booking = await session.scalar(
        select(Booking).where(Booking.id == booking_id).options(joinedload(Booking.quote))
    )
    if booking is None:
        raise DomainError(404, "booking_not_found", "Booking not found.")
    return booking
