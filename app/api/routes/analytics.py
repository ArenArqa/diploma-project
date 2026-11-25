from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import Dealer, Session
from app.core.clock import BUSINESS_TZ
from app.models import MarketSnapshot
from app.models.enums import ListingType
from app.schemas.analytics import InventorySummary, MarketSnapshotRead
from app.schemas.common import OffsetQuery, Page
from app.services.analytics import date_window, inventory_summary
from app.services.inventory import offset_page

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/market", response_model=Page[MarketSnapshotRead])
async def market(
    model_id: UUID,
    listing_type: ListingType,
    actor: Dealer,
    session: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    start, end = date_window(start_date, end_date, 90)
    query = (
        select(MarketSnapshot)
        .where(
            MarketSnapshot.model_id == model_id,
            MarketSnapshot.listing_type == listing_type,
            MarketSnapshot.as_of >= datetime.combine(start, time.min, BUSINESS_TZ),
            MarketSnapshot.as_of < datetime.combine(end + timedelta(days=1), time.min, BUSINESS_TZ),
        )
        .order_by(MarketSnapshot.as_of.desc())
    )
    return await offset_page(session, query, MarketSnapshotRead, OffsetQuery(limit=limit, offset=offset))


@router.get("/inventory", response_model=InventorySummary)
async def inventory(
    actor: Dealer, session: Session, start_date: date | None = None, end_date: date | None = None
):
    return await inventory_summary(session, actor, start_date, end_date)
