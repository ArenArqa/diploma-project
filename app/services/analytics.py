from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text

from app.core import clock
from app.core.exceptions import DomainError
from app.models import Booking, Car, CarModel, Listing, MarketSnapshot, RentalQuote, User, ValuationBaseline
from app.models.enums import BookingStatus, ListingStatus, ListingType, Role
from app.pricing_engine.depreciation import sale_factors
from app.pricing_engine.statistics import calibrate, quartiles


def date_window(start, end, max_days, default_days=30):
    end = end or clock.today()
    start = start or end - timedelta(days=default_days - 1)
    if end < start or (end - start).days >= max_days:
        raise DomainError(422, "invalid_date_window", f"Choose a date window of 1–{max_days} days.")
    return start, end


async def inventory_summary(session, actor, start, end):
    start, end = date_window(start, end, 365)
    listings = (
        select(Listing.listing_type, func.count()).join(Car).where(Listing.status == ListingStatus.active)
    )
    bookings = (
        select(func.count(Booking.id), func.coalesce(func.sum(RentalQuote.total_price_amd), 0))
        .join(RentalQuote, Booking.quote_id == RentalQuote.id)
        .join(Car, Booking.car_id == Car.id)
        .where(
            Booking.status == BookingStatus.confirmed, Booking.start_date >= start, Booking.start_date <= end
        )
    )
    if actor.role != Role.admin:
        listings, bookings = (
            listings.where(Car.owner_id == actor.id),
            bookings.where(Car.owner_id == actor.id),
        )
    counts = dict((await session.execute(listings.group_by(Listing.listing_type))).all())
    count, value = (await session.execute(bookings)).one()
    return {
        "period_start": start,
        "period_end": end,
        "active_sale_listing_count": counts.get(ListingType.sale, 0),
        "active_rental_listing_count": counts.get(ListingType.rent, 0),
        "confirmed_booking_count": count,
        "booked_value_amd": value,
    }


async def recalculate_market(session):
    """Caller owns a REPEATABLE READ transaction. All snapshots commit as one batch."""
    if not await session.scalar(text("SELECT pg_try_advisory_xact_lock(7342109)")):
        return 0
    instant, today = clock.now(), clock.today()
    recent_start = today - timedelta(days=89)
    recent_instant = datetime.combine(recent_start, time.min, clock.BUSINESS_TZ)
    rental_end = today + timedelta(days=29)
    baselines = {b.model_id: b for b in (await session.scalars(select(ValuationBaseline))).all()}
    rows = (
        await session.execute(
            select(Listing, Car)
            .join(Car)
            .join(User, Car.owner_id == User.id)
            .where(Listing.status == ListingStatus.active, User.is_active.is_(True))
        )
    ).all()
    rental_car_ids = {car.id for listing, car in rows if listing.listing_type == ListingType.rent}
    occupied = {}
    if rental_car_ids:
        reservations = (
            await session.scalars(
                select(Booking).where(
                    Booking.car_id.in_(rental_car_ids),
                    Booking.status == BookingStatus.confirmed,
                    Booking.start_date <= rental_end,
                    Booking.end_date >= today,
                )
            )
        ).all()
        for booking in reservations:
            days = (min(booking.end_date, rental_end) - max(booking.start_date, today)).days + 1
            occupied[booking.car_id] = occupied.get(booking.car_id, 0) + days
    model_ids = (await session.scalars(select(CarModel.id))).all()
    grouped = {}
    for listing, car in rows:
        grouped.setdefault((car.model_id, listing.listing_type), []).append((listing, car))
    for model_id in model_ids:
        for kind in ListingType:
            fleet = grouped.get((model_id, kind), [])
            metrics = {}
            if kind == ListingType.sale:
                comparable = [
                    (listing, car)
                    for listing, car in fleet
                    if recent_instant <= listing.price_updated_at <= instant
                ]
                baseline = baselines.get(model_id)
                ratios, ages = [], []
                if baseline:
                    for listing, car in comparable:
                        f = sale_factors(car.year, car.mileage_km, car.condition, today.year)
                        ratios.append(
                            float(
                                listing.price_amd
                                / (baseline.base_price_amd * f.age * f.mileage * f.condition)
                            )
                        )
                        ages.append(max(0, (instant - listing.price_updated_at).total_seconds() / 86400))
                    multiplier, mad = calibrate(ratios, ages)
                    metrics.update(
                        sale_market_multiplier=multiplier,
                        residual_log_mad=mad,
                        baseline_version=baseline.version,
                    )
                sample_count = len(ratios)
                prices = [listing.price_amd for listing, _ in comparable]
                window_start, window_end = recent_start, today
            else:
                prices = [listing.price_amd for listing, _ in fleet]
                sample_count = len(fleet)
                capacity = len(fleet) * 30
                used = sum(occupied.get(car.id, 0) for _, car in fleet)
                metrics.update(
                    occupied_car_days=used,
                    available_car_days=capacity,
                    occupancy_ratio=Decimal(used) / capacity if capacity else None,
                )
                window_start, window_end = today, rental_end
            p25, median, p75 = quartiles(prices)
            session.add(
                MarketSnapshot(
                    model_id=model_id,
                    listing_type=kind,
                    as_of=instant,
                    window_start=window_start,
                    window_end=window_end,
                    listing_count=len(fleet),
                    sample_count=sample_count,
                    median_price_amd=median,
                    p25_price_amd=p25,
                    p75_price_amd=p75,
                    **metrics,
                )
            )
    await session.flush()
    return len(model_ids) * 2
