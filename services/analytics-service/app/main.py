import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.kafka_consumer import consume
from app.routers.analytics import router as analytics_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB and start Kafka consumer background task."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized.")

    logger.info("Starting Kafka consumer background task...")
    consumer_task = asyncio.create_task(consume())

    yield

    logger.info("Shutting down Kafka consumer...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("Kafka consumer task cancelled.")


app = FastAPI(
    title="Analytics Service",
    description="Analytics and metrics service for the Telegram flower shop bot",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(analytics_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "analytics-service"}
