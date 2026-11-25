from sqlalchemy import select

from app.models import MarketSnapshot


async def latest_snapshot(session, model_id, listing_type):
    return await session.scalar(
        select(MarketSnapshot)
        .where(
            MarketSnapshot.model_id == model_id,
            MarketSnapshot.listing_type == listing_type,
        )
        .order_by(MarketSnapshot.as_of.desc())
        .limit(1)
    )
