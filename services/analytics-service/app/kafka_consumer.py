import asyncio
import json
import logging
import os
from datetime import datetime

from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from app.database import async_session
from app.models import OrderMetric, PopularProduct, ProductView

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPICS = ["product_views", "order_events"]
RETRY_DELAY_SECONDS = 5


async def _handle_product_view(data: dict) -> None:
    """Handle a product_view event: insert ProductView and upsert PopularProduct."""
    async with async_session() as session:
        async with session.begin():
            view = ProductView(
                product_id=data["product_id"],
                user_id=data.get("user_id"),
                viewed_at=datetime.utcnow(),
            )
            session.add(view)

            result = await session.execute(
                select(PopularProduct).where(
                    PopularProduct.product_id == data["product_id"]
                )
            )
            popular = result.scalar_one_or_none()

            if popular is not None:
                popular.view_count += 1
                popular.last_updated = datetime.utcnow()
            else:
                popular = PopularProduct(
                    product_id=data["product_id"],
                    product_name=data.get("product_name", "Unknown"),
                    view_count=1,
                    order_count=0,
                    last_updated=datetime.utcnow(),
                )
                session.add(popular)


async def _handle_order_created(data: dict) -> None:
    """Handle an order_created event: insert OrderMetric and upsert PopularProduct for each item."""
    async with async_session() as session:
        async with session.begin():
            metric = OrderMetric(
                order_id=data["order_id"],
                user_id=data["user_id"],
                total_amount=data["total_amount"],
                items_count=data["items_count"],
                delivery_type=data.get("delivery_type", "unknown"),
                created_at=datetime.utcnow(),
            )
            session.add(metric)

            items = data.get("items", [])
            for item in items:
                product_id = item["product_id"]
                product_name = item.get("product_name", "Unknown")

                result = await session.execute(
                    select(PopularProduct).where(
                        PopularProduct.product_id == product_id
                    )
                )
                popular = result.scalar_one_or_none()

                if popular is not None:
                    popular.order_count += 1
                    popular.last_updated = datetime.utcnow()
                else:
                    popular = PopularProduct(
                        product_id=product_id,
                        product_name=product_name,
                        view_count=0,
                        order_count=1,
                        last_updated=datetime.utcnow(),
                    )
                    session.add(popular)


async def consume() -> None:
    """Start the Kafka consumer loop with graceful reconnection handling."""
    while True:
        consumer = None
        try:
            consumer = AIOKafkaConsumer(
                *TOPICS,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id="analytics-service",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
            )
            await consumer.start()
            logger.info("Kafka consumer started, subscribed to %s", TOPICS)

            async for message in consumer:
                try:
                    data = message.value
                    event_type = data.get("event_type", "")

                    if message.topic == "product_views" or event_type == "product_view":
                        await _handle_product_view(data)
                        logger.debug("Processed product_view event: %s", data)
                    elif message.topic == "order_events" or event_type == "order_created":
                        await _handle_order_created(data)
                        logger.debug("Processed order_created event: %s", data)
                    else:
                        logger.warning(
                            "Unknown event type '%s' on topic '%s'",
                            event_type,
                            message.topic,
                        )
                except Exception:
                    logger.exception("Error processing Kafka message: %s", message.value)

        except Exception:
            logger.exception(
                "Kafka consumer connection error, retrying in %d seconds...",
                RETRY_DELAY_SECONDS,
            )
            await asyncio.sleep(RETRY_DELAY_SECONDS)
        finally:
            if consumer is not None:
                try:
                    await consumer.stop()
                except Exception:
                    logger.exception("Error stopping Kafka consumer")
