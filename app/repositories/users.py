from sqlalchemy import func, select

from app.models import User


async def by_email(session, email: str):
    return await session.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
