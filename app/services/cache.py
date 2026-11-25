import logging

from redis.exceptions import RedisError

from app.core.redis import get_redis

log = logging.getLogger(__name__)
GENERATION_KEY = "catalog:generation"


async def invalidate_catalog():
    try:
        await get_redis().incr(GENERATION_KEY)
    except (RedisError, OSError):
        log.warning("Catalog invalidation unavailable; cached responses expire within 60 seconds")
