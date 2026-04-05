import asyncio
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import aiohttp

from provider.schemas import (
    ProviderCreatePaymentRequest,
    ProviderPaymentResponse,
    ProviderWebhookPayload,
)

logger = logging.getLogger(__name__)


def _sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@dataclass
class ProviderPayment:
    id: str
    external_invoice_id: str
    amount: int
    callback_url: str
    status: str


class ProviderService:
    """Minimal in-memory provider emulator with async webhook callback."""

    def __init__(self) -> None:
        self._payments: dict[str, ProviderPayment] = {}
        self._timeout = aiohttp.ClientTimeout(total=10)
        self._tasks: set[asyncio.Task[None]] = set()

    def create_payment(self, payload: ProviderCreatePaymentRequest) -> ProviderPaymentResponse:
        amount_minor_units = self._parse_amount(payload.amount)
        payment_id = str(uuid4())
        payment = ProviderPayment(
            id=payment_id,
            external_invoice_id=payload.external_invoice_id,
            amount=amount_minor_units,
            callback_url=payload.callback_url,
            status="Created",
        )
        self._payments[payment_id] = payment

        task = asyncio.create_task(self._send_webhook(payment))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        return ProviderPaymentResponse(
            id=payment.id,
            external_invoice_id=payment.external_invoice_id,
            amount=payment.amount,
            callback_url=payment.callback_url,
            status=payment.status,
        )

    @staticmethod
    def _parse_amount(raw_amount: str) -> int:
        try:
            amount = Decimal(raw_amount)
        except InvalidOperation as exc:
            raise ValueError("amount must be a decimal string") from exc

        if amount <= 0:
            raise ValueError("amount must be greater than zero")

        return int(amount * 100)

    async def _send_webhook(self, payment: ProviderPayment) -> None:
        await asyncio.sleep(0.5)

        final_status = self._resolve_final_status(payment)
        payment.status = final_status

        callback_payload = ProviderWebhookPayload(
            id=payment.id,
            external_invoice_id=payment.external_invoice_id,
            status=final_status,
        )
        body = json.dumps(
            callback_payload.model_dump(),
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        webhook_secret = os.getenv("PROVIDER_WEBHOOK_SECRET", "change-me-provider-webhook-secret")
        signature = _sign_payload(body, webhook_secret)

        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            try:
                async with session.post(
                    payment.callback_url,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Provider-Signature": signature,
                    },
                ) as response:
                    if response.status >= 400:
                        logger.warning(
                            "Provider callback failed: payment_id=%s status=%s",
                            payment.id,
                            response.status,
                        )
            except Exception:
                logger.exception("Provider callback request error for payment_id=%s", payment.id)

    @staticmethod
    def _resolve_final_status(payment: ProviderPayment) -> str:
        return "Completed" if payment.amount % 2 == 0 else "Canceled"
