from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import Admin, Session
from app.core import clock
from app.core.exceptions import DomainError
from app.models import Booking, Car, Listing, User
from app.models.enums import BookingStatus, ListingStatus, ListingType, Role
from app.schemas.common import OffsetQuery, Page
from app.schemas.user import RoleUpdate, UserRead
from app.services.inventory import offset_page
from app.services.transactions import transaction

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users", response_model=Page[UserRead])
async def users(actor: Admin, session: Session, params: Annotated[OffsetQuery, Query()]):
    return await offset_page(
        session, select(User).order_by(User.created_at.desc(), User.id.desc()), UserRead, params
    )


@router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_role(user_id: UUID, data: RoleUpdate, actor: Admin, session: Session):
    async with transaction(session):
        user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
        if not user:
            raise DomainError(404, "user_not_found", "User not found.")
        if user.role == Role.admin:
            raise DomainError(403, "admin_role_reserved", "Admin accounts are managed through the CLI.")
        if data.role == "user":
            active = await session.scalar(
                select(Listing.id)
                .join(Car)
                .where(
                    Car.owner_id == user_id,
                    Listing.listing_type == ListingType.rent,
                    Listing.status == ListingStatus.active,
                )
                .limit(1)
            )
            unfinished = await session.scalar(
                select(Booking.id)
                .join(Car, Booking.car_id == Car.id)
                .where(
                    Car.owner_id == user_id,
                    Booking.status == BookingStatus.confirmed,
                    Booking.end_date >= clock.today(),
                )
                .limit(1)
            )
            if active or unfinished:
                raise DomainError(
                    409,
                    "dealer_has_rentals",
                    "Archive rental inventory after reservations finish before demotion.",
                )
        user.role = Role(data.role)
        await session.flush()
        result = UserRead.model_validate(user)
    return result
