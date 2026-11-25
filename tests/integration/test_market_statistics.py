import asyncio
import os
import subprocess
import sys
from datetime import timedelta

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

from app.core import clock
from app.models import MarketSnapshot
from app.tasks.market_statistics import recalculate_market_task, run_recalculation
from tests.factories import make_quote

pytestmark = pytest.mark.integration


async def test_snapshot_metrics_and_stale_fallback(client, db, inventory, headers):
    quote = await make_quote(client, headers["user"], inventory.listings[0], offset=5, duration=3)
    await client.post("/api/v1/bookings", headers=headers["user"], json={"quote_id": quote["id"]})
    assert await run_recalculation() == 2
    result = await client.get(
        "/api/v1/analytics/market",
        headers=headers["dealer"],
        params={"model_id": str(inventory.model), "listing_type": "rent"},
    )
    snapshot = result.json()["items"][0]
    assert snapshot["occupied_car_days"] == 3
    assert snapshot["available_car_days"] == 60
    assert snapshot["occupancy_ratio"] == "0.050000"
    fresh = await make_quote(client, headers["user"], inventory.listings[1])
    assert fresh["snapshot_status"] == "fresh"
    async with db() as session, session.begin():
        await session.execute(update(MarketSnapshot).values(as_of=clock.now() - timedelta(minutes=11)))
    stale = await make_quote(client, headers["user"], inventory.listings[1])
    assert stale["snapshot_status"] == "stale" and float(stale["demand_multiplier"]) == 1


async def test_sale_valuation_and_tenant_insights(client, inventory, headers):
    result = await client.post(
        "/api/v1/valuations/sale",
        json={"model_id": str(inventory.model), "year": 2020, "mileage_km": 75000, "condition": "good"},
    )
    assert result.status_code == 200, result.text
    assert result.json()["range_kind"] == "heuristic"
    assert result.json()["snapshot_status"] == "missing"
    dealer = (await client.get("/api/v1/analytics/inventory", headers=headers["dealer"])).json()
    admin = (await client.get("/api/v1/analytics/inventory", headers=headers["admin"])).json()
    assert dealer["active_sale_listing_count"] == 0
    assert admin["active_sale_listing_count"] == 1


async def test_overlapping_market_job_skips_when_lock_held(db, inventory):
    async with db() as session, session.begin():
        await session.execute(text("SELECT pg_advisory_xact_lock(7342109)"))
        assert await run_recalculation() == 0
    assert await run_recalculation() == 2


@pytest.mark.parametrize(
    "partial",
    [
        {"median_price_amd": 100, "p25_price_amd": None, "p75_price_amd": 120},
        {"occupied_car_days": 5, "available_car_days": None},
    ],
)
async def test_database_rejects_partial_metric_groups(db, inventory, partial):
    with pytest.raises(IntegrityError) as error:
        async with db() as session, session.begin():
            session.add(
                MarketSnapshot(
                    model_id=inventory.model,
                    listing_type="rent",
                    as_of=clock.now(),
                    window_start=clock.today(),
                    window_end=clock.today(),
                    listing_count=1,
                    sample_count=1,
                    **partial,
                )
            )
    assert error.value.orig.sqlstate == "23514"


async def test_actual_celery_worker_persists_snapshots(db, inventory, tmp_path):
    logfile = (tmp_path / "worker.log").open("w+")
    worker = subprocess.Popen(
        [
            str(__import__("pathlib").Path(sys.executable).with_name("celery")),
            "-A",
            "app.tasks.celery_app:celery_app",
            "worker",
            "--pool=solo",
            "--concurrency=1",
            "--without-gossip",
            "--without-mingle",
            "--without-heartbeat",
            "--loglevel=INFO",
        ],
        env=os.environ.copy(),
        stdout=logfile,
        stderr=subprocess.STDOUT,
    )
    try:
        await asyncio.to_thread(recalculate_market_task.delay)
        for _ in range(100):
            async with db() as session:
                count = await session.scalar(select(func.count()).select_from(MarketSnapshot))
            if count:
                assert count == 2
                break
            if worker.poll() is not None:
                logfile.seek(0)
                pytest.fail(logfile.read())
            await asyncio.sleep(0.1)
        else:
            logfile.seek(0)
            pytest.fail("Worker did not write snapshots: " + logfile.read())
    finally:
        worker.terminate()
        try:
            await asyncio.to_thread(worker.wait, timeout=5)
        except subprocess.TimeoutExpired:
            worker.kill()
            await asyncio.to_thread(worker.wait)
        logfile.close()
