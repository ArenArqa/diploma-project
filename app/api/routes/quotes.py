from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import Actor, Session
from app.schemas.quote import RentalQuoteCreate, RentalQuoteRead
from app.services.quotes import create_quote, read_quote

router = APIRouter(tags=["Rental quotes"])


@router.post("/rental-quotes", response_model=RentalQuoteRead, status_code=201)
async def add_quote(data: RentalQuoteCreate, actor: Actor, session: Session):
    return await create_quote(session, actor, data)


@router.get("/rental-quotes/{quote_id}", response_model=RentalQuoteRead)
async def get_quote(quote_id: UUID, actor: Actor, session: Session):
    return await read_quote(session, actor, quote_id)
