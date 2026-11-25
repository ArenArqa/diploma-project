from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile
from sqlalchemy import select

from app.api.dependencies import Actor, Session
from app.models import Car
from app.repositories.inventory import car_options, get_car, require_owner
from app.schemas.car import CarCreate, CarPrivateRead, CarUpdate
from app.schemas.common import OffsetQuery, Page
from app.services.images import upload_car_image
from app.services.inventory import car_read, create_car, offset_page, update_car

router = APIRouter(tags=["Cars"])


@router.post(
    "/cars/{car_id}/image",
    response_model=CarPrivateRead,
    responses={413: {"description": "Image exceeds 5 MB"}, 415: {"description": "Unsupported image type"}},
)
async def set_car_image(car_id: UUID, actor: Actor, session: Session, file: Annotated[UploadFile, File()]):
    return await upload_car_image(session, actor, car_id, file)


@router.post("/cars", response_model=CarPrivateRead, status_code=201)
async def add_car(data: CarCreate, actor: Actor, session: Session):
    return await create_car(session, actor, data)


@router.get("/me/cars", response_model=Page[CarPrivateRead])
async def my_cars(actor: Actor, session: Session, params: Annotated[OffsetQuery, Query()]):
    query = (
        select(Car)
        .where(Car.owner_id == actor.id)
        .options(*car_options())
        .order_by(Car.created_at.desc(), Car.id.desc())
    )
    return await offset_page(session, query, CarPrivateRead, params, lambda c: car_read(c, private=True))


@router.get("/cars/{car_id}", response_model=CarPrivateRead)
async def read_car(car_id: UUID, actor: Actor, session: Session):
    car = await get_car(session, car_id)
    require_owner(car, actor)
    return car_read(car, private=True)


@router.patch("/cars/{car_id}", response_model=CarPrivateRead)
async def edit_car(car_id: UUID, data: CarUpdate, actor: Actor, session: Session):
    return await update_car(session, actor, car_id, data)
