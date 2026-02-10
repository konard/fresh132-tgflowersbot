import json
import logging
import os

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

producer: AIOKafkaProducer | None = None


async def start_kafka_producer() -> None:
    global producer
    try:
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await producer.start()
        logger.info("Kafka producer started (bootstrap_servers=%s)", KAFKA_BOOTSTRAP_SERVERS)
    except Exception:
        logger.warning(
            "Failed to connect to Kafka at %s. Events will not be published.",
            KAFKA_BOOTSTRAP_SERVERS,
            exc_info=True,
        )
        producer = None


async def stop_kafka_producer() -> None:
    global producer
    if producer is not None:
        await producer.stop()
        producer = None
        logger.info("Kafka producer stopped")


async def send_event(topic: str, event: dict) -> None:
    if producer is None:
        logger.warning("Kafka producer is not initialised; event dropped: %s", event)
        return
    try:
        await producer.send_and_wait(topic, event)
        logger.info("Event sent to topic '%s': %s", topic, event)
    except Exception:
        logger.exception("Failed to send event to topic '%s'", topic)
