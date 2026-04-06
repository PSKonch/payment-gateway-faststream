from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_cache.decorator import cache

from app.api.dependencies import get_current_merchant_id, get_uow
from app.api.schemas import MerchantProfileResponse
from app.core.cache import merchant_cache_key_builder
from app.core.config import settings
from app.services import WebhookService
from app.uow import UnitOfWork

router = APIRouter(prefix="/api/v1", tags=["merchants"])


@router.get("/me", response_model=MerchantProfileResponse)  # type: ignore[misc]
@cache(
    expire=settings.CACHE_TTL_SECONDS,
    namespace="merchant-profile",
    key_builder=merchant_cache_key_builder,
)  # type: ignore[misc]
async def get_merchant_profile(
    merchant_id: UUID = Depends(get_current_merchant_id),
    uow: UnitOfWork = Depends(get_uow),
) -> MerchantProfileResponse:
    service = WebhookService(uow)
    data = await service.get_merchant_data(merchant_id)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found",
        )

    return MerchantProfileResponse(**data)
