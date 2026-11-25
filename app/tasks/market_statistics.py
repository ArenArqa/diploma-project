import asyncio

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.services.analytics import recalculate_market
from app.tasks.celery_app import celery_app


async def run_recalculation(database_url=None):
    engine = create_async_engine(
        database_url or get_settings().database_url, isolation_level="REPEATABLE READ"
    )
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session, session.begin():
            return await recalculate_market(session)
    finally:
        await engine.dispose()


@celery_app.task(
    name="marketplace.recalculate_market",
    autoretry_for=(OperationalError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def recalculate_market_task():
    return asyncio.run(run_recalculation())
