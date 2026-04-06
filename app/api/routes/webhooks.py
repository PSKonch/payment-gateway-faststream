import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from app.api.dependencies import get_uow
from app.api.schemas import WebhookPaymentRequest
from app.services import WebhookService
from app.uow import UnitOfWork

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/provider")  # type: ignore[misc]
async def receive_provider_webhook(
    request: Request,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    body = await request.body()

    try:
        request_data = WebhookPaymentRequest.model_validate_json(body)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        ) from e

    logger.info(
        "Webhook received: payment_id=%s external_invoice_id=%s status=%s",
        request_data.id,
        request_data.external_invoice_id,
        request_data.status,
    )

    service = WebhookService(uow)

    success = await service.handle_provider_webhook(
        external_invoice_id=request_data.external_invoice_id,
        provider_payment_id=request_data.id,
        provider_status=request_data.status,
    )

    if not success:
        logger.warning("Webhook processing failed: %s", request_data.external_invoice_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook processing failed",
        )

    logger.info("Webhook processed successfully: %s", request_data.external_invoice_id)
    return {"status": "ok"}
