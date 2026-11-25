from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import session_factory
from app.core.exceptions import DomainError
from app.core.security import decode_token
from app.models import User
from app.models.enums import Role

bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def session_dependency():
    async with session_factory()() as session:
        yield session


async def optional_user(token: Annotated[str | None, Depends(bearer)]):
    if not token:
        return None
    try:
        user_id = UUID(decode_token(token)["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
        raise DomainError(401, "invalid_token", "Invalid or expired access token.") from exc
    # Authentication owns a separate short-lived read session, so business services
    # can start their write transaction before their first domain query.
    async with session_factory()() as session:
        user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise DomainError(401, "inactive_account", "Account is unavailable.")
    return user


async def current_user(user=Depends(optional_user)):
    if user is None:
        raise DomainError(401, "authentication_required", "Sign in to continue.")
    return user


async def dealer_user(user=Depends(current_user)):
    if user.role not in (Role.dealer, Role.admin):
        raise DomainError(403, "dealer_required", "Dealer or admin access required.")
    return user


async def admin_user(user=Depends(current_user)):
    if user.role != Role.admin:
        raise DomainError(403, "admin_required", "Admin access required.")
    return user


Session = Annotated[AsyncSession, Depends(session_dependency)]
Actor = Annotated[User, Depends(current_user)]
Dealer = Annotated[User, Depends(dealer_user)]
Admin = Annotated[User, Depends(admin_user)]
Visitor = Annotated[User | None, Depends(optional_user)]
