import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.dependencies import get_uow
from app.api.schemas import WebhookPaymentRequest
from app.core.config import settings
from app.services import SignatureService, WebhookService
from app.uow import UnitOfWork

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/provider")  # type: ignore[misc]
async def receive_provider_webhook(
    request: Request,
    x_provider_signature: Annotated[str, Header(alias="X-Provider-Signature")],
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, str]:
    body = await request.body()

    if not SignatureService.verify_signature(
        body, x_provider_signature, settings.PROVIDER_WEBHOOK_SECRET
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid provider signature",
        )

    request_data = WebhookPaymentRequest.model_validate_json(body)

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
