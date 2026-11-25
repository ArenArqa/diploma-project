import argparse
import asyncio
import getpass

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import password_hasher
from app.models import User
from app.models.enums import Role
from app.schemas.auth import RegisterRequest
from app.services.transactions import transaction


async def create(email, full_name, password):
    data = TypeAdapter(RegisterRequest).validate_python(
        {"email": email, "full_name": full_name, "password": password}
    )
    engine = create_async_engine(get_settings().database_url)
    try:
        async with async_sessionmaker(engine)() as session, transaction(session):
            session.add(
                User(
                    email=str(data.email),
                    full_name=data.full_name,
                    role=Role.admin,
                    password_hash=password_hasher.hash(data.password.get_secret_value()),
                )
            )
        print("Admin created.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create an admin without exposing its password in shell history"
    )
    parser.add_argument("email")
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()
    asyncio.run(create(args.email, args.name, getpass.getpass("Admin password: ")))
