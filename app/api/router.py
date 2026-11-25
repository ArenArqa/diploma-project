from fastapi import APIRouter

from app.api.routes import (
    admin,
    analytics,
    auth,
    bookings,
    cars,
    health,
    listings,
    quotes,
    reference,
    users,
    valuations,
)

router = APIRouter(prefix="/api/v1")
for module in [
    auth,
    users,
    reference,
    cars,
    listings,
    valuations,
    quotes,
    bookings,
    analytics,
    admin,
    health,
]:
    router.include_router(module.router)
