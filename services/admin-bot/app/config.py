import os

BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")

ORDER_SERVICE_URL: str = os.getenv("ORDER_SERVICE_URL", "http://order-service:8002")
CATALOG_SERVICE_URL: str = os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8001")
ANALYTICS_SERVICE_URL: str = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8003")
