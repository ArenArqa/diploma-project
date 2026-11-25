from sqlalchemy import func, select

from app.core import clock
from app.core.exceptions import DomainError
from app.models import Car, CarModel, Listing, PriceHistory
from app.models.enums import ListingStatus, ListingType, Role
from app.repositories.bookings import has_unfinished
from app.repositories.inventory import get_car, get_listing, lock_inventory_owner, require_owner
from app.schemas.car import CarPrivateRead, CarPublicRead
from app.schemas.common import Page
from app.schemas.listing import ListingRead
from app.services.cache import invalidate_catalog
from app.services.transactions import transaction


def car_read(car, private=False):
    values = {
        field: getattr(car, field)
        for field in [
            "id",
            "year",
            "mileage_km",
            "fuel_type",
            "transmission",
            "condition",
            "color",
            "image_url",
        ]
    }
    values.update(brand=car.model.brand, model=car.model)
    if private:
        values.update(
            {field: getattr(car, field) for field in ["owner_id", "vin", "created_at", "updated_at"]}
        )
    return (CarPrivateRead if private else CarPublicRead)(**values)


def listing_read(listing):
    return ListingRead(
        **{
            field: getattr(listing, field)
            for field in [
                "id",
                "listing_type",
                "status",
                "title",
                "description",
                "city",
                "price_amd",
                "created_at",
                "updated_at",
            ]
        },
        car=car_read(listing.car),
        owner={field: getattr(listing.car.owner, field) for field in ["id", "full_name", "role"]},
    )


async def create_car(session, actor, data):
    async with transaction(session):
        if not await session.get(CarModel, data.model_id):
            raise DomainError(404, "model_not_found", "Model not found.")
        car = Car(owner_id=actor.id, **data.model_dump())
        session.add(car)
        await session.flush()
        response = car_read(await get_car(session, car.id), private=True)
    return response


async def update_car(session, actor, car_id, data):
    async with transaction(session):
        car = await get_car(session, car_id, lock=True)
        require_owner(car, actor)
        if await has_unfinished(session, car.id):
            raise DomainError(
                409, "car_reserved", "Specifications cannot change until existing rentals finish."
            )
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(car, key, value)
        await session.flush()
        await session.refresh(car, ["updated_at"])
        response = car_read(car, private=True)
    await invalidate_catalog()
    return response


async def create_listing(session, actor, data):
    async with transaction(session):
        await lock_inventory_owner(session, car_id=data.car_id)
        car = await get_car(session, data.car_id, lock=True)
        require_owner(car, actor)
        # Check the owner's role as well: an admin cannot give a user rental inventory indirectly.
        if data.listing_type == ListingType.rent and car.owner.role not in (Role.dealer, Role.admin):
            raise DomainError(403, "dealer_required", "Rental listings require a dealer account.")
        if await has_unfinished(session, car.id):
            raise DomainError(409, "car_reserved", "Existing rentals must finish before relisting.")
        listing = Listing(**data.model_dump())
        session.add(listing)
        await session.flush()
        session.add(
            PriceHistory(
                listing_id=listing.id, new_price_amd=listing.price_amd, changed_by=actor.id, reason="initial"
            )
        )
        response = listing_read(await get_listing(session, listing.id))
    await invalidate_catalog()
    return response


async def update_listing(session, actor, listing_id, data):
    async with transaction(session):
        await lock_inventory_owner(session, listing_id=listing_id)
        listing = await get_listing(session, listing_id, lock=True)
        require_owner(listing.car, actor)
        changes = data.model_dump(exclude_unset=True)
        if listing.status == ListingStatus.sold:
            raise DomainError(409, "listing_sold", "A sold listing is terminal.")
        target = changes.get("status", listing.status)
        if target == ListingStatus.sold and listing.listing_type != ListingType.sale:
            raise DomainError(422, "invalid_status", "Only sale listings can be marked sold.")
        if target == ListingStatus.active and listing.listing_type == ListingType.rent:
            if listing.car.owner.role not in (Role.dealer, Role.admin):
                raise DomainError(403, "dealer_required", "Rental listings require a dealer account.")
        if target != listing.status and await has_unfinished(session, listing.car_id):
            raise DomainError(
                409, "car_reserved", "Existing rentals must finish before changing listing status."
            )
        new_price = changes.get("price_amd", listing.price_amd)
        if new_price != listing.price_amd:
            session.add(
                PriceHistory(
                    listing_id=listing.id,
                    old_price_amd=listing.price_amd,
                    new_price_amd=new_price,
                    changed_by=actor.id,
                    reason="admin_update" if actor.role == Role.admin else "owner_update",
                )
            )
            listing.price_updated_at = clock.now()
        for key, value in changes.items():
            setattr(listing, key, value)
        await session.flush()
        await session.refresh(listing, ["updated_at"])
        response = listing_read(listing)
    await invalidate_catalog()
    return response


async def offset_page(session, query, schema, params, serializer=None):
    total = await session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = (await session.scalars(query.limit(params.limit).offset(params.offset))).unique().all()
    items = [(serializer(row) if serializer else schema.model_validate(row)) for row in rows]
    return Page[schema](items=items, limit=params.limit, offset=params.offset, total=total)
