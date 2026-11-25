from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.exceptions import DomainError
from app.models import Car, CarModel, Listing, User
from app.models.enums import Role


def car_options():
    return (joinedload(Car.model).joinedload(CarModel.brand), joinedload(Car.owner))


def listing_options():
    return (
        joinedload(Listing.car).joinedload(Car.model).joinedload(CarModel.brand),
        joinedload(Listing.car).joinedload(Car.owner),
    )


async def lock_inventory_owner(session, *, car_id=None, listing_id=None):
    """Serialize publication with role changes; acquire owner before car locks."""
    query = select(Car.owner_id)
    if listing_id is not None:
        query = query.join(Listing).where(Listing.id == listing_id)
    else:
        query = query.where(Car.id == car_id)
    owner_id = await session.scalar(query)
    if owner_id is not None:
        await session.execute(select(User.id).where(User.id == owner_id).with_for_update())


async def get_car(session, car_id, *, lock=False):
    if lock:
        await session.execute(select(Car.id).where(Car.id == car_id).with_for_update())
    car = await session.scalar(select(Car).where(Car.id == car_id).options(*car_options()))
    if car is None:
        raise DomainError(404, "car_not_found", "Car not found.")
    return car


async def get_listing(session, listing_id, *, lock=False):
    if lock:
        car_id = await session.scalar(select(Listing.car_id).where(Listing.id == listing_id))
        if car_id is None:
            raise DomainError(404, "listing_not_found", "Listing not found.")
        await get_car(session, car_id, lock=True)
    listing = await session.scalar(
        select(Listing).where(Listing.id == listing_id).options(*listing_options())
    )
    if listing is None:
        raise DomainError(404, "listing_not_found", "Listing not found.")
    return listing


def require_owner(car, actor):
    if actor.id != car.owner_id and actor.role != Role.admin:
        raise DomainError(404, "car_not_found", "Car not found.")


def require_visible(listing, actor=None):
    if actor and (actor.id == listing.car.owner_id or actor.role == Role.admin):
        return
    if listing.status != "active" or not listing.car.owner.is_active:
        raise DomainError(404, "listing_not_found", "Listing not found.")
