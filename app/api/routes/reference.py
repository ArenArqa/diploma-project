from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import Session
from app.models import Brand, CarModel
from app.schemas.reference import BrandRead, ModelRead

router = APIRouter(tags=["Reference data"])


@router.get("/brands", response_model=list[BrandRead])
async def brands(session: Session):
    return (await session.scalars(select(Brand).order_by(Brand.name))).all()


@router.get("/models", response_model=list[ModelRead])
async def models(session: Session, brand_id: UUID | None = None):
    query = select(CarModel).order_by(CarModel.name)
    if brand_id:
        query = query.where(CarModel.brand_id == brand_id)
    return (await session.scalars(query)).all()
