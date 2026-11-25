from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.dependencies import Actor, Dealer, Session
from app.core import clock
from app.core.exceptions import DomainError
from app.models import Booking, Car
from app.models.enums import BookingStatus, ListingType, Role
from app.repositories.bookings import get_booking
from app.repositories.inventory import get_listing, require_visible
from app.schemas.booking import AvailabilityRead, BookingCancel, BookingCreate, BookingRead
from app.schemas.common import OffsetQuery, Page
from app.services.bookings import accept_quote, booking_read, cancel_booking, require_participant
from app.services.inventory import offset_page

router = APIRouter(tags=["Bookings"])


@router.get("/listings/{listing_id}/availability", response_model=AvailabilityRead)
async def availability(listing_id: UUID, start_date: date, end_date: date, session: Session):
    if start_date < clock.today() or end_date < start_date or end_date > clock.today() + timedelta(days=365):
        raise DomainError(422, "invalid_calendar_window", "Choose dates between today and 365 days ahead.")
    listing = await get_listing(session, listing_id)
    require_visible(listing)
    if listing.listing_type != ListingType.rent:
        raise DomainError(422, "rental_required", "Choose a rental listing.")
    rows = (
        await session.scalars(
            select(Booking)
            .where(
                Booking.car_id == listing.car_id,
                Booking.status == BookingStatus.confirmed,
                Booking.start_date <= end_date,
                Booking.end_date >= start_date,
            )
            .order_by(Booking.start_date)
        )
    ).all()
    return AvailabilityRead(
        listing_id=listing_id,
        start_date=start_date,
        end_date=end_date,
        blocked_intervals=[
            {"start_date": max(start_date, b.start_date), "end_date": min(end_date, b.end_date)} for b in rows
        ],
    )


@router.post("/bookings", response_model=BookingRead, status_code=201)
async def book(data: BookingCreate, actor: Actor, session: Session, response: Response):
    result, created = await accept_quote(session, actor, data.quote_id)
    response.status_code = 201 if created else 200
    return result


@router.get("/me/bookings", response_model=Page[BookingRead])
async def my_bookings(
    actor: Actor,
    session: Session,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    status: BookingStatus | None = None,
):
    query = select(Booking).where(Booking.renter_id == actor.id).options(joinedload(Booking.quote))
    if status:
        query = query.where(Booking.status == status)
    return await offset_page(
        session,
        query.order_by(Booking.created_at.desc(), Booking.id.desc()),
        BookingRead,
        OffsetQuery(limit=limit, offset=offset),
        booking_read,
    )


@router.get("/me/rental-reservations", response_model=Page[BookingRead])
async def rental_reservations(
    actor: Dealer,
    session: Session,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    status: BookingStatus | None = None,
):
    query = select(Booking).join(Car, Booking.car_id == Car.id).options(joinedload(Booking.quote))
    if actor.role != Role.admin:
        query = query.where(Car.owner_id == actor.id)
    if status:
        query = query.where(Booking.status == status)
    return await offset_page(
        session,
        query.order_by(Booking.created_at.desc(), Booking.id.desc()),
        BookingRead,
        OffsetQuery(limit=limit, offset=offset),
        booking_read,
    )


@router.get("/bookings/{booking_id}", response_model=BookingRead)
async def read_booking(booking_id: UUID, actor: Actor, session: Session):
    booking = await get_booking(session, booking_id)
    await require_participant(session, booking, actor)
    return booking_read(booking)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingRead)
async def cancel(booking_id: UUID, data: BookingCancel, actor: Actor, session: Session):
    return await cancel_booking(session, actor, booking_id, data.reason)
