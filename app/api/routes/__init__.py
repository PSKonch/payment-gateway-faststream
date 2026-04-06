from app.api.routes.merchants import router as merchants_router
from app.api.routes.payments import router as payments_router
from app.api.routes.webhooks import router as webhooks_router

__all__ = ["merchants_router", "payments_router", "webhooks_router"]
