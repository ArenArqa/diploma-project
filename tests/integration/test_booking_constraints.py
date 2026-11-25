from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core import clock
from app.models import Booking
from tests.factories import make_quote

pytestmark = pytest.mark.integration


async def test_database_rejects_overlap_without_application(client, db, inventory, headers):
    q1 = await make_quote(client, headers["user"], inventory.listings[0])
    q2 = await make_quote(client, headers["user"], inventory.listings[0])
    assert (
        await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": q1["id"]})
    ).status_code == 201
    with pytest.raises(IntegrityError) as exc:
        async with db() as session, session.begin():
            session.add(
                Booking(
                    quote_id=q2["id"],
                    car_id=inventory.cars[0],
                    renter_id=inventory.users["user"].id,
                    start_date=clock.today() + timedelta(days=5),
                    end_date=clock.today() + timedelta(days=7),
                )
            )
    assert exc.value.orig.sqlstate == "23P01"


async def test_quote_terms_cannot_be_forged_in_database(client, db, inventory, headers):
    quote = await make_quote(client, headers["user"], inventory.listings[0])
    with pytest.raises(IntegrityError) as exc:
        async with db() as session, session.begin():
            session.add(
                Booking(
                    quote_id=quote["id"],
                    car_id=inventory.cars[1],
                    renter_id=inventory.users["user"].id,
                    start_date=clock.today() + timedelta(days=5),
                    end_date=clock.today() + timedelta(days=7),
                )
            )
    assert exc.value.orig.sqlstate == "23503"


async def test_inclusive_boundary_and_next_day(client, inventory, headers):
    quote = await make_quote(client, headers["user"], inventory.listings[0], offset=5, duration=3)
    await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
    shared = clock.today() + timedelta(days=7)
    result = await client.post(
        "/api/v1/rental-quotes",
        headers=headers["user"],
        json={"listing_id": str(inventory.listings[0]), "start_date": str(shared), "end_date": str(shared)},
    )
    assert result.status_code == 409
    next_quote = await make_quote(client, headers["user"], inventory.listings[0], offset=8, duration=1)
    assert next_quote["days"] == 1
    assert (
        await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": next_quote["id"]})
    ).status_code == 201


async def test_gist_constraint_exists(db):
    async with db() as session:
        definition = await session.scalar(
            text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='bookings_no_overlap'")
        )
        assert "EXCLUDE USING gist" in definition
