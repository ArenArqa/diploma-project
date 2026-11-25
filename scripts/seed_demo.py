"""Explicit, additive synthetic demo seed. Existing demo users/inventory are never overwritten."""

import asyncio
import csv
import os
import random
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import clock
from app.core.config import get_settings
from app.core.security import password_hasher
from app.models import (
    Booking,
    Brand,
    Car,
    CarModel,
    Listing,
    PriceHistory,
    RentalQuote,
    User,
    ValuationBaseline,
)
from app.models.enums import Condition, FuelType, ListingType, Role, Transmission
from app.pricing_engine.rental import price_rental
from app.pricing_engine.types import money
from app.pricing_engine.valuation import estimate_sale
from app.tasks.market_statistics import run_recalculation
from scripts.update_car_images import assign_model_photos, model_photo_urls, retire_generic_renders


def stable_id(name):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"autometric-demo/{name}")


async def seed(database_url=None):
    password = os.environ.get("DEMO_PASSWORD", "")
    if not 12 <= len(password) <= 128:
        raise SystemExit("Set DEMO_PASSWORD to 12–128 characters before seeding.")
    from scripts.install_car_photos import install_photos

    install_photos()
    photos = model_photo_urls()
    url = database_url or get_settings().database_url
    engine = create_async_engine(url)
    rng, instant, today = random.Random(42), clock.now(), clock.today()
    hashed = password_hasher.hash(password)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session, session.begin():
            users = {}
            for role in Role:
                email = f"{role.value}@demo.example.com"
                user = await session.scalar(select(User).where(User.email == email))
                if user is None:
                    user = User(
                        id=stable_id(email),
                        email=email,
                        password_hash=hashed,
                        full_name=f"Demo {role.value.title()}",
                        role=role,
                    )
                    session.add(user)
                    await session.flush()
                if user.role != role:
                    raise SystemExit(f"Existing {email} has a different role; seed does not alter accounts.")
                users[role] = user
            with (Path(__file__).resolve().parents[1] / "data/demo_baselines.csv").open() as source:
                baseline_rows = list(csv.DictReader(source))
            brands = {}
            for row in baseline_rows:
                brand = brands.get(row["brand_slug"])
                if brand is None:
                    brand = await session.scalar(select(Brand).where(Brand.slug == row["brand_slug"]))
                    if brand is None:
                        brand = Brand(
                            id=stable_id(row["brand_slug"]), name=row["brand"], slug=row["brand_slug"]
                        )
                        session.add(brand)
                        await session.flush()
                    brands[row["brand_slug"]] = brand
                model = await session.scalar(
                    select(CarModel).where(CarModel.brand_id == brand.id, CarModel.slug == row["model_slug"])
                )
                if model is None:
                    model = CarModel(
                        id=stable_id(f"{row['brand_slug']}/{row['model_slug']}"),
                        brand_id=brand.id,
                        name=row["model"],
                        slug=row["model_slug"],
                    )
                    session.add(model)
                    await session.flush()
                baseline = await session.get(ValuationBaseline, model.id)
                if baseline is None:
                    baseline = ValuationBaseline(
                        model_id=model.id,
                        base_price_amd=Decimal(row["base_price_amd"]),
                        source="synthetic_demo",
                        version="demo-v1",
                    )
                    session.add(baseline)
                for index in range(24):
                    kind = ListingType.sale if index < 20 else ListingType.rent
                    listing_id = stable_id(f"listing/{model.id}/{index}")
                    age = rng.randint(0, 17)
                    mileage = max(0, age * 15000 + rng.randint(-10000, 65000))
                    condition = rng.choice(list(Condition))
                    owner = (
                        users[Role.user]
                        if kind == ListingType.sale and index % 3 == 0
                        else users[Role.dealer]
                    )
                    raw = estimate_sale(
                        baseline=baseline.base_price_amd,
                        year=today.year - age,
                        mileage_km=mileage,
                        condition=condition,
                        current_year=today.year,
                    )
                    price = money(raw["recommended_price"] * Decimal(str(rng.lognormvariate(0, 0.12))))
                    if kind == ListingType.rent:
                        price = Decimal(rng.randrange(12000, 45001, 1000))
                    observed = instant - timedelta(days=rng.randint(0, 80), minutes=1)
                    existing = await session.get(Listing, listing_id)
                    choices = photos[(row["brand_slug"], row["model_slug"])]
                    image_url = choices[index % len(choices)]
                    if existing:
                        continue
                    car_id = stable_id(f"car/{model.id}/{index}")
                    car = Car(
                        id=car_id,
                        owner_id=owner.id,
                        model_id=model.id,
                        vin=f"D{car_id.int % (10**16):016d}",
                        year=today.year - age,
                        mileage_km=mileage,
                        condition=condition,
                        fuel_type=rng.choice(list(FuelType)),
                        transmission=Transmission.automatic,
                        color=rng.choice(["White", "Silver", "Black", "Blue"]),
                        image_url=image_url,
                    )
                    session.add(car)
                    await session.flush()
                    listing = Listing(
                        id=listing_id,
                        car_id=car.id,
                        listing_type=kind,
                        title=f"{row['brand']} {row['model']}",
                        city=rng.choice(["Yerevan", "Gyumri", "Vanadzor"]),
                        description="Synthetic diploma demonstration listing. All baseline prices are illustrative.",
                        price_amd=price,
                        price_updated_at=observed,
                        created_at=observed,
                    )
                    session.add(listing)
                    await session.flush()
                    original = money(price * Decimal("1.04"))
                    session.add_all(
                        [
                            PriceHistory(
                                listing_id=listing.id,
                                new_price_amd=original,
                                changed_by=owner.id,
                                reason="initial",
                                changed_at=observed - timedelta(days=7),
                            ),
                            PriceHistory(
                                listing_id=listing.id,
                                old_price_amd=original,
                                new_price_amd=price,
                                changed_by=owner.id,
                                reason="owner_update",
                                changed_at=observed,
                            ),
                        ]
                    )
                    if kind == ListingType.rent:
                        # One future reservation per rental car, plus a separated past example.
                        for offset, duration in [(2 + (index - 20) * 7, 3 + index % 3), (-14, 4)]:
                            start, end = (
                                today + timedelta(days=offset),
                                today + timedelta(days=offset + duration - 1),
                            )
                            calculation = price_rental(price, start, end)
                            calculation["snapshot_status"] = "missing"
                            quote = RentalQuote(
                                id=stable_id(f"quote/{listing_id}/{offset}"),
                                listing_id=listing.id,
                                car_id=car.id,
                                renter_id=users[Role.user].id,
                                start_date=start,
                                end_date=end,
                                base_daily_rate_amd=price,
                                total_price_amd=calculation["total_price_amd"],
                                pricing_version="rent-v1",
                                pricing_breakdown=calculation,
                                created_at=instant - timedelta(days=20),
                                expires_at=instant - timedelta(days=20) + timedelta(minutes=10),
                            )
                            session.add(quote)
                            await session.flush()
                            session.add(
                                Booking(
                                    quote_id=quote.id,
                                    car_id=car.id,
                                    renter_id=users[Role.user].id,
                                    start_date=start,
                                    end_date=end,
                                )
                            )
            # Existing generic renders and missing images migrate to exact-model photographs.
            await assign_model_photos(session)
        retire_generic_renders()
        # Remove only legacy bundled illustrations after their database paths are replaced.
        for legacy in (Path(__file__).resolve().parents[1] / "frontend/uploads/cars").glob("demo-*.svg"):
            legacy.unlink()
        # Expire cached public listing payloads after backfilling images.
        from app.services.cache import invalidate_catalog

        await invalidate_catalog()
        count = await run_recalculation(url)
        print(f"Demo ready: user/dealer/admin@demo.example.com. Market snapshots written: {count}.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
