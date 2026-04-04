from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_merchant_id, get_uow
from app.api.schemas import PaymentCreateRequest, PaymentListResponse, PaymentResponse
from app.core.config import settings
from app.services import PaymentService
from app.uow import UnitOfWork

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)  # type: ignore[misc]
async def create_payment(
    request: PaymentCreateRequest,
    merchant_id: UUID = Depends(get_current_merchant_id),
    uow: UnitOfWork = Depends(get_uow),
) -> PaymentResponse:
    service = PaymentService(uow)
    webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/provider"

    payment = await service.create_payment(
        merchant_id=merchant_id,
        merchant_order_id=request.merchant_order_id,
        amount=request.amount,
        webhook_url=webhook_url,
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment creation failed: insufficient balance or duplicate order",
        )

    return PaymentResponse.model_validate(payment)


@router.get("", response_model=PaymentListResponse)  # type: ignore[misc]
async def get_payments(
    merchant_id: UUID = Depends(get_current_merchant_id),
    status_filter: str | None = None,
    cursor: datetime | None = None,
    limit: int = 100,
    uow: UnitOfWork = Depends(get_uow),
) -> PaymentListResponse:
    service = PaymentService(uow)

    payments = await service.get_merchant_payments(
        merchant_id=merchant_id,
        status=status_filter,
        cursor=cursor,
        limit=limit + 1,
    )

    has_more = len(payments) > limit
    items = payments[:limit]
    next_cursor = items[-1].created_at if has_more and items else None

    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in items],
        next_cursor=next_cursor,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)  # type: ignore[misc]
async def get_payment(
    payment_id: UUID,
    merchant_id: UUID = Depends(get_current_merchant_id),
    uow: UnitOfWork = Depends(get_uow),
) -> PaymentResponse:
    async with uow as u:
        payment = await u.payments.get_by_id(payment_id)

        if not payment or payment.merchant_id != merchant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        return PaymentResponse.model_validate(payment)
