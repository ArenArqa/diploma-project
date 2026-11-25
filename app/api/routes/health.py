from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.database import session_factory
from app.core.redis import get_redis
from app.schemas.health import HealthRead, LiveRead

router = APIRouter(prefix="/health", tags=["Operations"])


@router.get("/live", response_model=LiveRead)
async def live():
    return {"status": "ok"}


@router.get("/ready", response_model=HealthRead, responses={503: {"model": HealthRead}})
async def ready():
    database, redis = "up", "up"
    try:
        async with session_factory()() as session:
            await session.execute(text("SELECT 1 FROM users LIMIT 1"))
    except Exception:
        database = "down"
    try:
        await get_redis().ping()
    except Exception:
        redis = "down"
    result = HealthRead(
        status="unavailable" if database == "down" else "degraded" if redis == "down" else "ok",
        database=database,
        redis=redis,
    )
    return JSONResponse(status_code=503 if database == "down" else 200, content=result.model_dump())
