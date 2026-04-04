import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
from aio_pika import ExchangeType

from app.core.config import settings

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


class MessageConsumer:
    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._handlers: dict[str, MessageHandler] = {}

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(settings.BROKER_URL)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)
        logger.info("Consumer connected to RabbitMQ")

    async def disconnect(self) -> None:
        if self._channel:
            await self._channel.close()
        if self._connection:
            await self._connection.close()
        logger.info("Consumer disconnected from RabbitMQ")

    def register_handler(self, routing_key: str, handler: MessageHandler) -> None:
        self._handlers[routing_key] = handler

    async def start_consuming(self, queue_name: str, routing_keys: list[str]) -> None:
        if not self._channel:
            raise RuntimeError("Consumer not connected")

        exchange = await self._channel.declare_exchange(
            "payments",
            ExchangeType.TOPIC,
            durable=True,
        )

        queue = await self._channel.declare_queue(queue_name, durable=True)

        for routing_key in routing_keys:
            await queue.bind(exchange, routing_key)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        body = json.loads(message.body.decode())
                        routing_key = message.routing_key or ""

                        handler = self._handlers.get(routing_key)
                        if handler:
                            await handler(body)
                        else:
                            logger.warning(f"No handler for routing key: {routing_key}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")


consumer = MessageConsumer()
