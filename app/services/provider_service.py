from typing import Any

import aiohttp

from app.core.config import settings


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
