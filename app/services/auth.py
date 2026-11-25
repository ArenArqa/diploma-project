from fastapi.concurrency import run_in_threadpool

from app.core.exceptions import DomainError
from app.core.security import DUMMY_HASH, create_token, password_hasher
from app.models import User
from app.repositories.users import by_email
from app.schemas.auth import TokenRead
from app.schemas.user import UserRead
from app.services.transactions import transaction


async def register(session, data):
    hashed = await run_in_threadpool(password_hasher.hash, data.password.get_secret_value())
    async with transaction(session):
        user = User(email=str(data.email), password_hash=hashed, full_name=data.full_name)
        session.add(user)
        await session.flush()
        response = UserRead.model_validate(user)
    return response


async def login(session, email, password):
    user = await by_email(session, email)
    valid = await run_in_threadpool(
        password_hasher.verify, password, user.password_hash if user else DUMMY_HASH
    )
    if not user or not valid or not user.is_active:
        raise DomainError(401, "invalid_credentials", "Invalid email or password.")
    return TokenRead(access_token=create_token(user.id))
