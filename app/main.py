from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.api.routes import merchants_router, payments_router, webhooks_router
from app.core.cache import close_cache, init_cache
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis_client: Any | None = None

    try:
        redis_client = await init_cache()
    except Exception:
        redis_client = None

    yield

    await close_cache(redis_client)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

app.include_router(payments_router)
app.include_router(merchants_router)
app.include_router(webhooks_router)


@app.get("/health")  # type: ignore[misc]
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
