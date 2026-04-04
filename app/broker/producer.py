import json
import logging
from typing import Any

import aio_pika
from aio_pika import ExchangeType

from app.core.config import settings

logger = logging.getLogger(__name__)


class MessageProducer:
    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(settings.BROKER_URL)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            "payments",
            ExchangeType.TOPIC,
            durable=True,
        )
        logger.info("Producer connected to RabbitMQ")

    async def disconnect(self) -> None:
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()
        logger.info("Producer disconnected from RabbitMQ")

    async def publish(self, routing_key: str, message: dict[str, Any]) -> None:
        if not self._exchange:
            raise RuntimeError("Producer not connected")

        body = json.dumps(message).encode()
        await self._exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )
        logger.debug(f"Published message to {routing_key}")


producer = MessageProducer()
