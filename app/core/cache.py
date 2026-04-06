from collections.abc import Callable
from contextlib import suppress
from hashlib import sha256
from typing import Any

from fastapi import Request, Response
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis  # type: ignore[import-untyped]

from app.core.config import settings


async def init_cache() -> Redis:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    await redis.ping()

    FastAPICache.init(
        RedisBackend(redis),
        prefix="payment-gateway-cache",
    )
    return redis


async def close_cache(redis: Redis | None) -> None:
    if redis is None:
        return

    with suppress(Exception):
        await redis.aclose()


def merchant_cache_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    request: Request | None = None,
    response: Response | None = None,
    *args: Any,
    **kwargs: Any,
) -> str:
    del response, args

    merchant_id = "anonymous"
    if "merchant_id" in kwargs:
        merchant_id = str(kwargs["merchant_id"])
    elif request is not None:
        api_key = request.headers.get("x-api-key", "")
        merchant_id = api_key.split(":", maxsplit=1)[0] if api_key else merchant_id

    path = request.url.path if request is not None else func.__name__
    query = request.url.query if request is not None else ""
    raw_key = f"{namespace}:{path}:{query}:{merchant_id}"
    return sha256(raw_key.encode()).hexdigest()
