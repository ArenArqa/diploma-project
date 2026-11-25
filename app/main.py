from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.core.config import get_settings
from app.core.database import get_engine
from app.core.exceptions import install_handlers
from app.core.logging import configure_logging
from app.core.redis import get_redis
from app.schemas.common import ErrorResponse

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


@asynccontextmanager
async def lifespan(app):
    get_settings()
    configure_logging()
    yield
    await get_redis().aclose()
    await get_engine().dispose()


app = FastAPI(
    title="Smart Car Marketplace & Rental Platform",
    version="0.1.0",
    lifespan=lifespan,
    description="AMD marketplace with explainable synthetic valuation and overlap-safe rentals.",
    responses={status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422)},
)
install_handlers(app)
app.include_router(router)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
app.mount("/uploads/cars", StaticFiles(directory=FRONTEND / "uploads/cars"), name="car-images")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(FRONTEND / "index.html")
