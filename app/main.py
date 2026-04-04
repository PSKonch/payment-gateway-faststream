import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import merchants_router, payments_router, webhooks_router
from app.broker import outbox_publisher, producer
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await producer.connect()
    outbox_task = asyncio.create_task(outbox_publisher.start())

    yield

    await outbox_publisher.stop()
    outbox_task.cancel()
    await producer.disconnect()


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
