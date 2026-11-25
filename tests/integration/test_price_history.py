import pytest
from sqlalchemy.exc import IntegrityError

from app.models import PriceHistory

pytestmark = pytest.mark.integration


async def test_history_is_atomic_and_noop_not_recorded(client, inventory, headers):
    path = f"/api/v1/listings/{inventory.listings[2]}"
    assert (
        await client.patch(path, headers=headers["user"], json={"price_amd": "7500000"})
    ).status_code == 200
    assert (
        await client.patch(path, headers=headers["user"], json={"price_amd": "7500000"})
    ).status_code == 200
    history = (await client.get(path + "/price-history")).json()
    assert history["total"] == 2
    assert history["items"][0]["old_price_amd"] == "8000000"
    assert history["items"][0]["new_price_amd"] == "7500000"


async def test_database_rejects_update_history_without_old_price(db, inventory):
    with pytest.raises(IntegrityError) as error:
        async with db() as session, session.begin():
            session.add(
                PriceHistory(
                    listing_id=inventory.listings[0],
                    old_price_amd=None,
                    new_price_amd=15000,
                    changed_by=inventory.users["dealer"].id,
                    reason="owner_update",
                )
            )
    assert error.value.orig.sqlstate == "23514"
