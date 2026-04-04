import asyncio
from typing import Any

import aiohttp

from app.core.config import settings
from app.core.enums import PaymentStatus, ProviderStatus


class ProviderService:
    def __init__(self) -> None:
        self.base_url = settings.PROVIDER_URL
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def create_payment(
        self,
        external_invoice_id: str,
        amount: str,
        callback_url: str,
    ) -> dict[str, Any] | None:
        await asyncio.sleep(
            settings.PROVIDER_DELAY_MIN
            + (settings.PROVIDER_DELAY_MAX - settings.PROVIDER_DELAY_MIN) * 0.5
        )

        url = f"{self.base_url}/api/v1/payments"
        payload = {
            "external_invoice_id": external_invoice_id,
            "amount": amount,
            "callback_url": callback_url,
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 201:
                        return await resp.json()  # type: ignore[no-any-return]
                    return None
            except Exception:
                return None

    @staticmethod
    def map_provider_status(status: str) -> PaymentStatus:
        mapping: dict[str, PaymentStatus] = {
            ProviderStatus.CREATED: PaymentStatus.PROCESSING,
            ProviderStatus.COMPLETED: PaymentStatus.COMPLETED,
            ProviderStatus.CANCELED: PaymentStatus.CANCELED,
        }
        return mapping.get(status, PaymentStatus.FAILED) or PaymentStatus.FAILED
