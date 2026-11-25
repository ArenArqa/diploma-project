import os
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

os.environ.setdefault("JWT_SECRET", "test-only-secret-with-at-least-32-characters")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/14")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
if os.getenv("TEST_REDIS_URL"):
    os.environ["REDIS_URL"] = os.environ["TEST_REDIS_URL"]

from app.core.config import get_settings  # noqa: E402
from app.core.database import get_engine, session_factory  # noqa: E402
from app.core.redis import get_redis  # noqa: E402
from app.core.security import create_token, password_hasher  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Brand, Car, CarModel, Listing, PriceHistory, User, ValuationBaseline  # noqa: E402
from app.models.enums import Condition, FuelType, ListingType, Role, Transmission  # noqa: E402

PASSWORD = "TestPassword123!"


@pytest.fixture(scope="session")
def migrated_database():
    url = os.getenv("TEST_DATABASE_URL")
    redis_url = os.getenv("TEST_REDIS_URL")
    if not url or not redis_url:
        pytest.skip("Set TEST_DATABASE_URL and TEST_REDIS_URL to run real infrastructure tests")
    name = make_url(url).database or ""
    if not (name.endswith("_test") or name.startswith("test_")):
        pytest.fail("Integration tests require an explicitly named test database")
    if not redis_url.endswith("/15"):
        pytest.fail("TEST_REDIS_URL must use dedicated Redis database /15")
    subprocess.run(
        [
            str(__import__("pathlib").Path(__import__("sys").executable).with_name("alembic")),
            "upgrade",
            "head",
        ],
        check=True,
        env={**os.environ, "DATABASE_URL": url},
    )


@pytest_asyncio.fixture
async def db(migrated_database):
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_redis.cache_clear()
    async with session_factory()() as session, session.begin():
        await session.execute(
            text(
                "TRUNCATE bookings, rental_quotes, market_snapshots, listing_price_history, "
                "listings, cars, valuation_baselines, car_models, brands, users CASCADE"
            )
        )
    await get_redis().flushdb()
    yield session_factory()
    await get_redis().aclose()
    await get_engine().dispose()
    get_redis.cache_clear()
    get_engine.cache_clear()


@pytest_asyncio.fixture
async def client(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def inventory(db):
    hashed = password_hasher.hash(PASSWORD)
    users = {
        role: User(email=f"{role}@example.com", full_name=f"Test {role}", password_hash=hashed, role=role)
        for role in Role
    }
    outsider = User(email="outsider@example.com", full_name="Other user", password_hash=hashed)
    async with db() as session, session.begin():
        brand = Brand(name="Toyota", slug="toyota")
        session.add_all([*users.values(), outsider, brand])
        await session.flush()
        model = CarModel(brand_id=brand.id, name="Corolla", slug="corolla")
        session.add(model)
        await session.flush()
        session.add(ValuationBaseline(model_id=model.id, base_price_amd=11500000, version="demo-v1"))
        cars, listings = [], []
        for i in range(3):
            owner = users[Role.user] if i == 2 else users[Role.dealer]
            car = Car(
                owner_id=owner.id,
                model_id=model.id,
                vin=f"T{uuid4().int % 10**16:016d}",
                year=2020,
                mileage_km=75000,
                fuel_type=FuelType.gasoline,
                transmission=Transmission.automatic,
                condition=Condition.good,
            )
            session.add(car)
            await session.flush()
            listing = Listing(
                car_id=car.id,
                listing_type=ListingType.sale if i == 2 else ListingType.rent,
                title=f"Toyota Corolla {i}",
                description="Test car",
                city="Yerevan",
                price_amd=8000000 if i == 2 else 20000,
            )
            session.add(listing)
            await session.flush()
            session.add(
                PriceHistory(
                    listing_id=listing.id,
                    new_price_amd=listing.price_amd,
                    changed_by=owner.id,
                    reason="initial",
                )
            )
            cars.append(car.id)
            listings.append(listing.id)
        result = SimpleNamespace(
            users=users, outsider=outsider, brand=brand.id, model=model.id, cars=cars, listings=listings
        )
    return result


@pytest.fixture
def headers(inventory):
    return {
        **{
            role: {"Authorization": f"Bearer {create_token(user.id)}"}
            for role, user in inventory.users.items()
        },
        "outsider": {"Authorization": f"Bearer {create_token(inventory.outsider.id)}"},
    }
