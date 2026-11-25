import pytest

from tests.factories import make_quote

pytestmark = [pytest.mark.integration, pytest.mark.smoke]


async def test_defense_flow(client, inventory, headers):
    assert (await client.get("/")).status_code == 200
    assert (await client.get("/static/js/booking.js")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200
    assert (await client.get("/api/v1/health/ready")).json()["status"] == "ok"
    assert (await client.get("/api/v1/listings?listing_type=rent")).json()["total"] == 2
    quote = await make_quote(client, headers["user"], inventory.listings[0], duration=7)
    booking = (
        await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
    ).json()
    assert booking["phase"] == "upcoming"
    assert (await client.get("/api/v1/me/bookings", headers=headers["user"])).json()["total"] == 1
    assert (
        await client.post(f"/api/v1/bookings/{booking['id']}/cancel", headers=headers["user"], json={})
    ).json()["status"] == "cancelled"
