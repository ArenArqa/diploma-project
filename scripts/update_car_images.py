"""Rotate matching model photographs across existing demo cars, preserving uploads."""

import asyncio
from collections import defaultdict

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Brand, Car, CarModel, Listing
from app.models.enums import ListingStatus
from app.services.cache import invalidate_catalog
from scripts.fetch_car_images import local_name, source_records
from scripts.install_car_photos import UPLOADS, install_photos


def model_photo_urls():
    photos = defaultdict(list)
    for row, number, _ in source_records():
        photos[(row["brand_slug"], row["model_slug"])].append("/uploads/cars/" + local_name(row, number))
    return photos


async def assign_model_photos(session):
    photos = model_photo_urls()
    managed = {url for group in photos.values() for url in group}
    rows = (
        await session.execute(
            select(Car, Brand.slug, CarModel.slug, Listing.listing_type)
            .join(CarModel, Car.model_id == CarModel.id)
            .join(Brand, CarModel.brand_id == Brand.id)
            .outerjoin(Listing, and_(Listing.car_id == Car.id, Listing.status == ListingStatus.active))
            .order_by(
                Car.model_id, Listing.created_at.desc().nullslast(), Listing.id.desc().nullslast(), Car.id
            )
        )
    ).all()
    counters, changed = defaultdict(int), 0
    for car, brand, model, listing_type in rows:
        # User uploads have UUID filenames and are deliberately left untouched.
        if (
            car.image_url
            and car.image_url not in managed
            and not car.image_url.startswith("/uploads/cars/demo-")
        ):
            continue
        choices = photos.get((brand, model))
        if not choices:
            raise ValueError(
                f"No verified exact-model photos for {brand}/{model}; refusing a mismatched fallback"
            )
        # Sale and rental filters each retain alternating photos after filtering.
        group = (brand, model, listing_type)
        index = counters[group]
        counters[group] += 1
        image_url = choices[index % len(choices)]
        if car.image_url != image_url:
            car.image_url = image_url
            changed += 1
    await session.flush()
    return changed


def retire_generic_renders():
    """Remove only obsolete bundled renders after database URLs have committed."""
    for image in UPLOADS.glob("demo-photo-*.jpg"):
        image.unlink()


async def update():
    install_photos()
    engine = create_async_engine(get_settings().database_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session, session.begin():
            changed = await assign_model_photos(session)
        retire_generic_renders()
        await invalidate_catalog()
        print(f"Updated {changed} cars with exact-model photographs; custom uploads preserved.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update())
