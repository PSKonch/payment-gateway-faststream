import asyncio
import logging

from app.broker.producer import producer
from app.core.db import async_session
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class OutboxPublisher:
    def __init__(self, poll_interval: float = 1.0) -> None:
        self._poll_interval = poll_interval
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info("Outbox publisher started")

        while self._running:
            try:
                await self._process_pending_messages()
            except Exception as e:
                logger.error(f"Outbox processing error: {e}")

            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("Outbox publisher stopped")

    async def _process_pending_messages(self) -> None:
        async with UnitOfWork(async_session) as uow:
            messages = await uow.outbox.get_pending_messages(limit=100)

            for message in messages:
                try:
                    await uow.outbox.mark_as_processing(message.id)
                    await uow.commit()

                    await producer.publish(message.topic, message.payload)

                    await uow.outbox.mark_as_sent(message.id)
                    await uow.commit()

                    logger.debug(f"Published outbox message {message.id}")
                except Exception as e:
                    logger.error(f"Failed to publish message {message.id}: {e}")
                    await uow.outbox.mark_as_failed(message.id, str(e))
                    await uow.commit()


outbox_publisher = OutboxPublisher()
