import asyncio
from uuid import UUID

from app.broker.consumer import consumer
from app.broker.schemas import PaymentCreatedEvent
from app.core.config import settings
from app.core.db import async_session
from app.core.enums import PaymentStatus, ProviderStatus
from app.services import ProviderService
from app.uow import UnitOfWork

provider_service = ProviderService()


def build_webhook_callback_url() -> str:
    return f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/provider"


async def handle_payment_created(message: dict[str, object]) -> None:
    event = PaymentCreatedEvent.model_validate(message)

    await asyncio.sleep(
        settings.PROVIDER_DELAY_MIN
        + (settings.PROVIDER_DELAY_MAX - settings.PROVIDER_DELAY_MIN) * 0.5
    )

    async with UnitOfWork(async_session) as uow:
        payment = await uow.payments.get_by_id_for_update(UUID(event.payment_id))
        if payment is None:
            return

        if payment.status != PaymentStatus.CREATED:
            return

        callback_url = build_webhook_callback_url()
        provider_result = await provider_service.create_payment(
            external_invoice_id=event.external_invoice_id,
            amount=f"{event.amount / 100:.2f}",
            callback_url=callback_url,
        )

        if provider_result is None:
            raise RuntimeError(f"Provider request failed for payment {event.payment_id}")

        await uow.payments.update_status(
            payment.id,
            PaymentStatus.PROCESSING,
            provider_payment_id=provider_result["id"],
            provider_status=ProviderStatus.CREATED,
        )
        await uow.commit()


async def main() -> None:
    consumer.register_handler("payment.created", handle_payment_created)
    await consumer.connect()
    try:
        await consumer.start_consuming("gateway-payments", ["payment.created"])
    finally:
        await consumer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
