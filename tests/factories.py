from datetime import timedelta

from app.core import clock


async def make_quote(client, headers, listing_id, offset=5, duration=3):
    start = clock.today() + timedelta(days=offset)
    result = await client.post(
        "/api/v1/rental-quotes",
        headers=headers,
        json={
            "listing_id": str(listing_id),
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=duration - 1)).isoformat(),
        },
    )
    assert result.status_code == 201, result.text
    return result.json()
