from fastapi import APIRouter

from app.api.dependencies import Session
from app.schemas.valuation import SaleValuationRead, SaleValuationRequest
from app.services.valuation import value_car

router = APIRouter(tags=["Pricing"])


@router.post("/valuations/sale", response_model=SaleValuationRead)
async def sale_valuation(data: SaleValuationRequest, session: Session):
    return await value_car(session, data)
