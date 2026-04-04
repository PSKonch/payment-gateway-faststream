import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_uow
from app.api.schemas import WebhookPaymentRequest
from app.services import PaymentService
from app.uow import UnitOfWork

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/provider")  # type: ignore[misc]
async def receive_provider_webhook(
    request: WebhookPaymentRequest,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    logger.info(
        f"Webhook received: payment_id={request.id}, "
        f"external_invoice_id={request.external_invoice_id}, "
        f"status={request.status}"
    )

    service = PaymentService(uow)

    success = await service.handle_webhook(
        external_invoice_id=request.external_invoice_id,
        provider_payment_id=request.id,
        provider_status=request.status,
    )

    if not success:
        logger.warning(f"Webhook processing failed: {request.external_invoice_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook processing failed",
        )

    logger.info(f"Webhook processed successfully: {request.external_invoice_id}")
    return {"status": "ok"}
