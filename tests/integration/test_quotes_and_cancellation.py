from datetime import timedelta

import pytest
from sqlalchemy import update

from app.core import clock
from app.models import RentalQuote
from tests.factories import make_quote

pytestmark = pytest.mark.integration


async def test_frozen_price_retry_and_cancellation(client, inventory, headers):
    quote = await make_quote(client, headers["user"], inventory.listings[0])
    await client.patch(
        f"/api/v1/listings/{inventory.listings[0]}", headers=headers["dealer"], json={"price_amd": "40000"}
    )
    first = await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
    assert first.status_code == 201, first.text
    assert first.json()["total_price_amd"] == quote["total_price_amd"]
    retry = await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
    assert retry.status_code == 200 and retry.json()["id"] == first.json()["id"]
    path = f"/api/v1/bookings/{first.json()['id']}/cancel"
    assert (await client.post(path, headers=headers["outsider"], json={})).status_code == 404
    assert (await client.post(path, headers=headers["user"], json={})).status_code == 200
    assert (await client.post(path, headers=headers["user"], json={})).status_code == 200
    replacement = await make_quote(client, headers["user"], inventory.listings[0])
    assert (
        await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": replacement["id"]})
    ).status_code == 201


async def test_expired_foreign_and_self_quotes(client, db, inventory, headers):
    quote = await make_quote(client, headers["user"], inventory.listings[0])
    assert (
        await client.post("/api/v1/bookings", headers=headers["outsider"], json={"quote_id": quote["id"]})
    ).status_code == 404
    async with db() as session, session.begin():
        await session.execute(
            update(RentalQuote)
            .where(RentalQuote.id == quote["id"])
            .values(
                created_at=clock.now() - timedelta(minutes=20), expires_at=clock.now() - timedelta(minutes=10)
            )
        )
    expired = await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
    assert expired.status_code == 409 and expired.json()["error"]["code"] == "quote_expired"
    own = await client.post(
        "/api/v1/rental-quotes",
        headers=headers["dealer"],
        json={
            "listing_id": str(inventory.listings[0]),
            "start_date": quote["start_date"],
            "end_date": quote["end_date"],
        },
    )
    assert own.status_code == 403


async def test_availability_hides_identity(client, inventory, headers):
    quote = await make_quote(client, headers["user"], inventory.listings[0])
    await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
    result = await client.get(
        f"/api/v1/listings/{inventory.listings[0]}/availability",
        params={"start_date": quote["start_date"], "end_date": quote["end_date"]},
    )
    assert result.json()["blocked_intervals"] == [
        {"start_date": quote["start_date"], "end_date": quote["end_date"]}
    ]
    assert "renter" not in result.text


async def test_cancel_same_day_disallowed(client, inventory, headers):
    quote = await make_quote(client, headers["user"], inventory.listings[0], offset=0, duration=1)
    booking = (
        await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
    ).json()
    assert (
        await client.post(f"/api/v1/bookings/{booking['id']}/cancel", headers=headers["user"], json={})
    ).status_code == 409
