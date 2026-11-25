import asyncio

import pytest

from tests.factories import make_quote

pytestmark = pytest.mark.integration


async def test_twenty_competing_bookings(client, inventory, headers):
    quotes = [await make_quote(client, headers["user"], inventory.listings[0]) for _ in range(20)]
    results = await asyncio.gather(
        *[
            client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": q["id"]})
            for q in quotes
        ]
    )
    assert [r.status_code for r in results].count(201) == 1
    assert [r.status_code for r in results].count(409) == 19
    assert all(r.json()["error"]["code"] == "booking_overlap" for r in results if r.status_code == 409)


async def test_same_quote_concurrent_acceptance_is_idempotent(client, inventory, headers):
    quote = await make_quote(client, headers["user"], inventory.listings[0])
    results = await asyncio.gather(
        *[
            client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
            for _ in range(5)
        ]
    )
    assert sorted(r.status_code for r in results) == [200, 200, 200, 200, 201]
    assert len({r.json()["id"] for r in results}) == 1


async def test_independent_cars(client, inventory, headers):
    quotes = [await make_quote(client, headers["user"], identifier) for identifier in inventory.listings[:2]]
    results = await asyncio.gather(
        *[
            client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": q["id"]})
            for q in quotes
        ]
    )
    assert all(r.status_code == 201 for r in results)
