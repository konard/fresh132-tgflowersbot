import json
import logging
import os

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


class KafkaProducerWrapper:
    """Async Kafka producer that sends JSON-serialised events.

    The producer is designed to be resilient: if Kafka is unreachable the
    service continues to operate and errors are only logged.
    """

    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start the underlying AIOKafkaProducer.

        Connection failures are caught so that the catalog service can still
        serve HTTP requests even when Kafka is unavailable.
        """
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self._producer.start()
            logger.info("Kafka producer started (servers=%s)", KAFKA_BOOTSTRAP_SERVERS)
        except Exception:
            logger.warning(
                "Failed to connect to Kafka at %s. "
                "Events will not be published until reconnected.",
                KAFKA_BOOTSTRAP_SERVERS,
                exc_info=True,
            )
            self._producer = None

    async def stop(self) -> None:
        """Gracefully stop the producer."""
        if self._producer is not None:
            try:
                await self._producer.stop()
                logger.info("Kafka producer stopped")
            except Exception:
                logger.warning("Error stopping Kafka producer", exc_info=True)
            finally:
                self._producer = None

    async def send_event(self, topic: str, event_data: dict) -> None:
        """Send a JSON event to the given Kafka *topic*.

        If the producer is not connected the call is silently skipped so that
        the calling endpoint is never blocked by Kafka issues.
        """
        if self._producer is None:
            logger.debug(
                "Kafka producer unavailable; dropping event on topic '%s'", topic
            )
            return
        try:
            await self._producer.send_and_wait(topic, event_data)
            logger.debug("Event sent to topic '%s': %s", topic, event_data)
        except Exception:
            logger.warning(
                "Failed to send event to Kafka topic '%s'",
                topic,
                exc_info=True,
            )


# Module-level singleton used by the FastAPI app
kafka_producer = KafkaProducerWrapper()
