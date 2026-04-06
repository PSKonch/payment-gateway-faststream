import asyncio

from app.broker.outbox_publisher import outbox_publisher
from app.broker.producer import producer


async def main() -> None:
    await producer.connect()
    try:
        await outbox_publisher.start()
    finally:
        await outbox_publisher.stop()
        await producer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
