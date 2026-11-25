import asyncio

import pytest

from tests.factories import make_quote

pytestmark = pytest.mark.integration


async def test_user_cannot_rent_and_cannot_edit_others_car(client, inventory, headers):
    result = await client.post(
        "/api/v1/listings",
        headers=headers["user"],
        json={
            "car_id": str(inventory.cars[2]),
            "listing_type": "rent",
            "title": "Illegal rental",
            "city": "Yerevan",
            "price_amd": "15000",
        },
    )
    assert result.status_code == 403
    assert (
        await client.patch(
            f"/api/v1/cars/{inventory.cars[0]}", headers=headers["user"], json={"mileage_km": 100}
        )
    ).status_code == 404


async def test_reserved_inventory_cannot_be_archived_or_modified(client, inventory, headers):
    quote = await make_quote(client, headers["user"], inventory.listings[0])
    assert (
        await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
    ).status_code == 201
    assert (
        await client.patch(
            f"/api/v1/listings/{inventory.listings[0]}",
            headers=headers["dealer"],
            json={"status": "archived"},
        )
    ).status_code == 409
    assert (
        await client.patch(
            f"/api/v1/cars/{inventory.cars[0]}", headers=headers["dealer"], json={"mileage_km": 100}
        )
    ).status_code == 409


async def test_one_active_listing_even_concurrently(client, inventory, headers):
    await client.patch(
        f"/api/v1/listings/{inventory.listings[0]}", headers=headers["dealer"], json={"status": "archived"}
    )
    body = {
        "car_id": str(inventory.cars[0]),
        "listing_type": "rent",
        "title": "Relisted",
        "city": "Yerevan",
        "price_amd": "21000",
    }
    results = await asyncio.gather(
        *[client.post("/api/v1/listings", headers=headers["dealer"], json=body) for _ in range(2)]
    )
    assert sorted(r.status_code for r in results) == [201, 409]


async def test_patch_rejects_null_and_sale_terminal(client, inventory, headers):
    path = f"/api/v1/listings/{inventory.listings[2]}"
    assert (await client.patch(path, headers=headers["user"], json={"title": None})).status_code == 422
    assert (await client.patch(path, headers=headers["user"], json={"status": "sold"})).status_code == 200
    assert (await client.patch(path, headers=headers["user"], json={"status": "active"})).status_code == 409
    assert (await client.get(path)).status_code == 404
    assert (await client.get(path, headers=headers["user"])).status_code == 200
