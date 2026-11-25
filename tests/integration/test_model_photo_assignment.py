import pytest
from sqlalchemy import select

from app.models import Car
from scripts.update_car_images import assign_model_photos

pytestmark = pytest.mark.integration


async def test_model_assignment_replaces_generic_renders_and_preserves_uploads(db, inventory):
    async with db() as session, session.begin():
        managed = await session.get(Car, inventory.cars[0])
        managed.image_url = "/uploads/cars/demo-photo-wrong-brand.jpg"
        custom = await session.get(Car, inventory.cars[2])
        custom.image_url = "/uploads/cars/0123456789abcdef0123456789abcdef.jpg"
    async with db() as session, session.begin():
        assert await assign_model_photos(session) == 2
    async with db() as session, session.begin():
        assert await assign_model_photos(session) == 0
        cars = (await session.scalars(select(Car))).all()
        assigned = [car.image_url for car in cars if car.id != inventory.cars[2]]
        assert len(set(assigned)) == 2
        assert all(url.startswith("/uploads/cars/toyota/corolla_") for url in assigned)
        assert (
            await session.get(Car, inventory.cars[2])
        ).image_url == "/uploads/cars/0123456789abcdef0123456789abcdef.jpg"
