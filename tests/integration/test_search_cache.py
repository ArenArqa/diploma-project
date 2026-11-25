import pytest
from redis.exceptions import ConnectionError

from app.core.redis import get_redis
from app.services import search

pytestmark = pytest.mark.integration


async def test_cache_hit_and_invalidation(client, inventory, headers, monkeypatch):
    path = "/api/v1/listings?listing_type=sale"
    first = await client.get(path)
    assert first.status_code == 200
    original = search.search_query

    def forbidden(*args):
        raise AssertionError("Expected a cache hit")

    monkeypatch.setattr(search, "search_query", forbidden)
    assert (await client.get(path)).json() == first.json()
    monkeypatch.setattr(search, "search_query", original)
    await client.patch(
        f"/api/v1/listings/{inventory.listings[2]}", headers=headers["user"], json={"price_amd": "7000000"}
    )
    updated = await client.get(path)
    assert updated.json()["items"][0]["price_amd"] == "7000000"
    keys = [k async for k in get_redis().scan_iter("catalog:v1:*")]
    assert len(keys) == 2


async def test_redis_outage_falls_back(client, inventory, monkeypatch):
    async def unavailable(*args, **kwargs):
        raise ConnectionError("Simulated outage")

    monkeypatch.setattr(get_redis(), "get", unavailable)
    assert (await client.get("/api/v1/listings")).json()["total"] == 3
