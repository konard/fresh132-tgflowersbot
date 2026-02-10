import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .kafka_producer import kafka_producer
from .routers import categories, products, stores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the FastAPI application."""
    # --- Startup ---
    logger.info("Creating database tables ...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    logger.info("Starting Kafka producer ...")
    await kafka_producer.start()

    yield

    # --- Shutdown ---
    logger.info("Stopping Kafka producer ...")
    await kafka_producer.stop()

    logger.info("Disposing database engine ...")
    await engine.dispose()


app = FastAPI(
    title="Catalog Service",
    description="Microservice managing the flower-shop product catalog",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(categories.router)
app.include_router(products.router)
app.include_router(stores.router)


@app.get("/health", tags=["health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}
