from sqlalchemy import select

from app.core import clock
from app.core.exceptions import DomainError
from app.models import Booking, RentalQuote
from app.models.enums import BookingStatus, ListingStatus, Role
from app.repositories.bookings import ensure_available, get_booking
from app.repositories.inventory import get_car, get_listing
from app.schemas.booking import BookingRead
from app.services.quotes import quote_read, validate_dates
from app.services.transactions import transaction


def booking_read(booking):
    today = clock.today()
    phase = (
        "cancelled"
        if booking.status == BookingStatus.cancelled
        else "upcoming"
        if today < booking.start_date
        else "completed"
        if today > booking.end_date
        else "in_progress"
    )
    return BookingRead(
        **{
            field: getattr(booking, field)
            for field in [
                "id",
                "quote_id",
                "car_id",
                "renter_id",
                "start_date",
                "end_date",
                "status",
                "created_at",
                "cancelled_at",
                "cancellation_reason",
            ]
        },
        listing_id=booking.quote.listing_id,
        days=booking.quote.days,
        phase=phase,
        total_price_amd=booking.quote.total_price_amd,
        pricing_breakdown=quote_read(booking.quote, booking.id),
    )


async def require_participant(session, booking, actor):
    car = await get_car(session, booking.car_id)
    if actor.id not in (booking.renter_id, car.owner_id) and actor.role != Role.admin:
        raise DomainError(404, "booking_not_found", "Booking not found.")


async def accept_quote(session, actor, quote_id):
    async with transaction(session):
        quote = await session.get(RentalQuote, quote_id)
        if not quote or quote.renter_id != actor.id:
            raise DomainError(404, "quote_not_found", "Quote not found.")
        car = await get_car(session, quote.car_id, lock=True)
        existing_id = await session.scalar(select(Booking.id).where(Booking.quote_id == quote.id))
        if existing_id:
            return booking_read(await get_booking(session, existing_id)), False
        if quote.expires_at <= clock.now():
            raise DomainError(409, "quote_expired", "This quote expired. Request a new quote.")
        validate_dates(quote.start_date, quote.end_date)
        listing = await get_listing(session, quote.listing_id)
        if listing.status != ListingStatus.active or not car.owner.is_active:
            raise DomainError(409, "listing_unavailable", "This rental listing is no longer available.")
        if car.owner_id == actor.id:
            raise DomainError(403, "self_rental", "You cannot rent your own car.")
        await ensure_available(session, car.id, quote.start_date, quote.end_date)
        booking = Booking(
            quote_id=quote.id,
            car_id=car.id,
            renter_id=actor.id,
            start_date=quote.start_date,
            end_date=quote.end_date,
        )
        session.add(booking)
        await session.flush()
        response = booking_read(await get_booking(session, booking.id))
    return response, True


async def cancel_booking(session, actor, booking_id, reason):
    async with transaction(session):
        booking = await get_booking(session, booking_id)
        await get_car(session, booking.car_id, lock=True)
        # The first read may precede another transaction's cancellation.
        await session.refresh(booking)
        await session.refresh(booking, ["quote"])
        await require_participant(session, booking, actor)
        if booking.status == BookingStatus.cancelled:
            return booking_read(booking)
        if booking.start_date <= clock.today():
            raise DomainError(409, "rental_started", "Cancellation is only allowed before the start date.")
        booking.status = BookingStatus.cancelled
        booking.cancelled_at, booking.cancelled_by = clock.now(), actor.id
        booking.cancellation_reason = reason
        await session.flush()
        response = booking_read(booking)
    return response
