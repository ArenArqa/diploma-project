from contextlib import asynccontextmanager

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import DomainError


def database_conflict(exc):
    cause = getattr(exc.orig, "__cause__", None)
    name = getattr(cause, "constraint_name", "") or ""
    code = getattr(exc.orig, "sqlstate", "")
    if name == "bookings_no_overlap":
        return DomainError(409, "booking_overlap", "This car is already booked for those dates.")
    if name == "uq_one_active_listing_per_car":
        return DomainError(409, "active_listing_exists", "This car already has an active listing.")
    if code == "23505":
        return DomainError(409, "duplicate_record", "A record with this unique identifier already exists.")
    return None


@asynccontextmanager
async def transaction(session):
    try:
        async with session.begin():
            yield
    except IntegrityError as exc:
        error = database_conflict(exc)
        if error:
            raise error from exc
        raise
