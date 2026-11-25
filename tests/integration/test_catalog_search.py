import pytest

pytestmark = pytest.mark.integration


async def test_combined_search_and_private_fields(client, inventory):
    result = await client.get(
        "/api/v1/listings",
        params={
            "brand_id": str(inventory.brand),
            "model_id": str(inventory.model),
            "year_min": 2019,
            "year_max": 2021,
            "price_min": 19000,
            "price_max": 21000,
            "fuel_type": "gasoline",
            "mileage_max": 80000,
            "listing_type": "rent",
            "sort": "price_asc",
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["total"] == 2
    car = result.json()["items"][0]["car"]
    assert "vin" not in car and "owner_id" not in car
    assert "email" not in result.json()["items"][0]["owner"]


@pytest.mark.parametrize("sort", ["newest", "price_asc", "price_desc", "year_desc", "mileage_asc"])
async def test_cursor_pagination_with_ties(client, inventory, sort):
    params = {"pagination": "cursor", "limit": 1, "sort": sort, "listing_type": "rent"}
    first = (await client.get("/api/v1/listings", params=params)).json()
    assert first["next_cursor"]
    second = (await client.get("/api/v1/listings", params={**params, "cursor": first["next_cursor"]})).json()
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert second["next_cursor"] is None
    mismatch = await client.get(
        "/api/v1/listings", params={**params, "cursor": first["next_cursor"], "year_min": 2020}
    )
    assert mismatch.status_code == 422


async def test_search_validation(client, inventory):
    assert (await client.get("/api/v1/listings?year_min=2025&year_max=2020")).status_code == 422
    assert (await client.get("/api/v1/listings?sort=price_asc")).status_code == 422
    assert (await client.get("/api/v1/listings?limit=101")).status_code == 422
    assert (await client.get("/api/v1/listings?order_by=DROP%20TABLE")).status_code == 422
