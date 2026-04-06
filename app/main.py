from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

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


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return cast(dict[str, Any], app.openapi_schema)

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Добавляем security схему для мерчантов
    openapi_schema["components"]["securitySchemes"] = {
        "merchantAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Мерчант API ключ в формате <key_id>:<secret>",
        },
        "merchantSignature": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Signature",
            "description": "Опционально для dev-bypass key_id, обязательно для strict режима. "
            "HMAC-SHA256 подпись canonical request: METHOD\\nPATH\\nBODY_SHA256_HEX",
        },
    }

    # Обновляем операции для документации
    for path, path_item in openapi_schema["paths"].items():
        for method_name, operation in path_item.items():
            if method_name in ["post", "get", "put", "delete", "patch"]:
                # Вебхуки подписываются иначе (от провайдера)
                if "/webhooks/provider" in path:
                    operation["security"] = []

                    description_suffix = (
                        "Provider webhook uses callback_url from provider request and "
                        "expects JSON body with fields: id, external_invoice_id, status."
                    )
                    current_description = operation.get("description", "")
                    if description_suffix not in current_description:
                        operation["description"] = (
                            f"{current_description}\n\n{description_suffix}".strip()
                        )

                    if "x-provider-webhooks" not in operation:
                        operation["x-provider-webhooks"] = True

                # Для мерчантов всегда нужен X-API-Key; X-Signature зависит от режима auth
                elif "/health" not in path:
                    operation["security"] = [{"merchantAuth": []}]

    app.openapi_schema = openapi_schema
    return cast(dict[str, Any], app.openapi_schema)


app.openapi = custom_openapi


@app.get("/health")  # type: ignore[misc]
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}
