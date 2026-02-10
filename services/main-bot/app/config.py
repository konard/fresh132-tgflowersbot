"""Configuration for the main Telegram bot service."""

import os


BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")
ORDER_SERVICE_URL: str = os.getenv("ORDER_SERVICE_URL", "http://order-service:8002")
CATALOG_SERVICE_URL: str = os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8001")
KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
