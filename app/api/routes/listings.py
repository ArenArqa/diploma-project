from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import Actor, Session, Visitor
from app.models import Car, Listing, PriceHistory
from app.models.enums import ListingStatus, ListingType
from app.repositories.inventory import get_listing, listing_options, require_visible
from app.schemas.common import OffsetQuery, Page
from app.schemas.listing import (
    ListingCreate,
    ListingRead,
    ListingSearchQuery,
    ListingUpdate,
    PriceHistoryRead,
)
from app.services.inventory import create_listing, listing_read, offset_page, update_listing
from app.services.search import search_listings

router = APIRouter(tags=["Listings"])


@router.get("/listings", response_model=Page[ListingRead])
async def catalog(session: Session, params: Annotated[ListingSearchQuery, Query()]):
    return await search_listings(session, params)


@router.post("/listings", response_model=ListingRead, status_code=201)
async def add_listing(data: ListingCreate, actor: Actor, session: Session):
    return await create_listing(session, actor, data)


@router.get("/me/listings", response_model=Page[ListingRead])
async def my_listings(
    actor: Actor,
    session: Session,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
    status: ListingStatus | None = None,
    listing_type: ListingType | None = None,
):
    query = select(Listing).join(Car).where(Car.owner_id == actor.id).options(*listing_options())
    if status:
        query = query.where(Listing.status == status)
    if listing_type:
        query = query.where(Listing.listing_type == listing_type)
    return await offset_page(
        session,
        query.order_by(Listing.created_at.desc(), Listing.id.desc()),
        ListingRead,
        OffsetQuery(limit=limit, offset=offset),
        listing_read,
    )


@router.get("/listings/{listing_id}", response_model=ListingRead)
async def read_listing(listing_id: UUID, session: Session, actor: Visitor):
    listing = await get_listing(session, listing_id)
    require_visible(listing, actor)
    return listing_read(listing)


@router.patch("/listings/{listing_id}", response_model=ListingRead)
async def edit_listing(listing_id: UUID, data: ListingUpdate, actor: Actor, session: Session):
    return await update_listing(session, actor, listing_id, data)


@router.get("/listings/{listing_id}/price-history", response_model=Page[PriceHistoryRead])
async def price_history(
    listing_id: UUID, session: Session, actor: Visitor, params: Annotated[OffsetQuery, Query()]
):
    require_visible(await get_listing(session, listing_id), actor)
    query = (
        select(PriceHistory)
        .where(PriceHistory.listing_id == listing_id)
        .order_by(PriceHistory.changed_at.desc(), PriceHistory.id.desc())
    )
    return await offset_page(session, query, PriceHistoryRead, params)
