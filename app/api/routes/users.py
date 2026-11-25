from fastapi import APIRouter

from app.api.dependencies import Actor
from app.schemas.user import UserRead

router = APIRouter(tags=["Users"])


@router.get("/users/me", response_model=UserRead)
async def me(actor: Actor):
    return actor
