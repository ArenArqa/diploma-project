from datetime import timedelta

from sqlalchemy import select

from app.core import clock
from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models import Booking, RentalQuote
from app.models.enums import ListingType, Role
from app.pricing_engine.rental import price_rental
from app.repositories.analytics import latest_snapshot
from app.repositories.bookings import ensure_available
from app.repositories.inventory import get_listing, require_visible
from app.schemas.quote import RentalQuoteRead
from app.services.transactions import transaction
from app.services.valuation import snapshot_status


def validate_dates(start, end):
    if (
        start < clock.today()
        or end < start
        or end > clock.today() + timedelta(days=365)
        or (end - start).days >= 90
    ):
        raise DomainError(
            422, "invalid_rental_dates", "Use 1–90 inclusive days between today and 365 days ahead."
        )


def quote_read(quote, booking_id=None):
    breakdown = quote.pricing_breakdown
    return RentalQuoteRead(
        **{
            field: getattr(quote, field)
            for field in [
                "id",
                "listing_id",
                "car_id",
                "start_date",
                "end_date",
                "days",
                "base_daily_rate_amd",
                "total_price_amd",
                "market_snapshot_id",
                "pricing_version",
                "created_at",
                "expires_at",
            ]
        },
        effective_daily_rate_amd=breakdown["effective_daily_rate_amd"],
        demand_multiplier=breakdown["demand_multiplier"],
        snapshot_status=breakdown["snapshot_status"],
        daily_breakdown=breakdown["daily_breakdown"],
        accepted_booking_id=booking_id,
    )


async def create_quote(session, actor, data):
    async with transaction(session):
        validate_dates(data.start_date, data.end_date)
        listing = await get_listing(session, data.listing_id, lock=True)
        require_visible(listing)
        if listing.listing_type != ListingType.rent:
            raise DomainError(422, "rental_required", "Choose a rental listing.")
        if listing.car.owner_id == actor.id:
            raise DomainError(403, "self_rental", "You cannot rent your own car.")
        await ensure_available(session, listing.car_id, data.start_date, data.end_date)
        snapshot = await latest_snapshot(session, listing.car.model_id, ListingType.rent)
        status = snapshot_status(snapshot)
        result = price_rental(
            listing.price_amd,
            data.start_date,
            data.end_date,
            snapshot.occupancy_ratio if status == "fresh" else None,
        )
        result["snapshot_status"] = status
        quote = RentalQuote(
            listing_id=listing.id,
            car_id=listing.car_id,
            renter_id=actor.id,
            start_date=data.start_date,
            end_date=data.end_date,
            base_daily_rate_amd=listing.price_amd,
            total_price_amd=result["total_price_amd"],
            market_snapshot_id=snapshot.id if snapshot else None,
            pricing_version=result["pricing_version"],
            pricing_breakdown=result,
            created_at=clock.now(),
            expires_at=clock.now() + timedelta(minutes=get_settings().quote_minutes),
        )
        session.add(quote)
        await session.flush()
        response = quote_read(quote)
    return response


async def read_quote(session, actor, quote_id):
    quote = await session.get(RentalQuote, quote_id)
    if not quote or (quote.renter_id != actor.id and actor.role != Role.admin):
        raise DomainError(404, "quote_not_found", "Quote not found.")
    booking_id = await session.scalar(select(Booking.id).where(Booking.quote_id == quote.id))
    return quote_read(quote, booking_id)
