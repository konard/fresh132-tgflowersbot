import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_db, init_db
from app.kafka_producer import start_kafka_producer, stop_kafka_producer
from app.routers import cart, orders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Manage startup and shutdown of database and Kafka connections."""
    logger.info("Starting order-service...")
    await init_db()
    logger.info("Database initialised")
    await start_kafka_producer()
    logger.info("Kafka producer ready")
    yield
    logger.info("Shutting down order-service...")
    await stop_kafka_producer()
    await close_db()
    logger.info("Order-service stopped")


app = FastAPI(
    title="Order Service",
    description="Manages shopping carts and orders for the Telegram flower shop bot",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(cart.router)
app.include_router(orders.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "order-service"}
