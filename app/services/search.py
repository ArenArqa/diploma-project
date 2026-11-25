import hashlib
import logging

from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.core.redis import get_redis
from app.models import CarModel
from app.repositories.search import cursor_value, decode_cursor, encode_cursor, paginated_query, search_query
from app.schemas.common import Page
from app.schemas.listing import ListingRead
from app.services.cache import GENERATION_KEY
from app.services.inventory import listing_read

log = logging.getLogger(__name__)


async def search_listings(session, params):
    if params.cursor:
        decode_cursor(params)
    key = None
    redis = get_redis()
    try:
        generation = await redis.get(GENERATION_KEY) or "0"
        digest = hashlib.sha256(params.model_dump_json().encode()).hexdigest()
        key = f"catalog:v1:{generation}:{digest}"
        cached = await redis.get(key)
        if cached:
            return Page[ListingRead].model_validate_json(cached)
    except (RedisError, OSError, ValidationError):
        log.info("Search cache unavailable or invalid; querying PostgreSQL")
    if params.brand_id and params.model_id:
        model = await session.get(CarModel, params.model_id)
        if model is None or model.brand_id != params.brand_id:
            raise DomainError(422, "brand_model_mismatch", "The model does not belong to that brand.")
    query = search_query(params)
    total = (
        await session.scalar(select(func.count()).select_from(query.subquery()))
        if params.pagination == "offset"
        else None
    )
    rows = (await session.scalars(paginated_query(query, params).limit(params.limit + 1))).unique().all()
    has_more = len(rows) > params.limit
    rows = rows[: params.limit]
    cursor = None
    if has_more and rows and params.pagination == "cursor":
        cursor = encode_cursor(params, cursor_value(rows[-1], params.sort), rows[-1].id)
    response = Page[ListingRead](
        items=[listing_read(row) for row in rows],
        limit=params.limit,
        offset=params.offset if params.pagination == "offset" else None,
        total=total,
        next_cursor=cursor,
    )
    if key:
        try:
            await redis.set(key, response.model_dump_json(), ex=get_settings().cache_ttl_seconds)
        except (RedisError, OSError):
            pass
    return response
