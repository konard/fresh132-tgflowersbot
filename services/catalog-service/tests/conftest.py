"""Shared fixtures for catalog-service tests.

Uses an in-memory SQLite database and a mock Kafka producer so that tests
are fully self-contained and require no external infrastructure.
"""

from __future__ import annotations

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.kafka_producer import kafka_producer
from app.main import app
from app.models import Category, Product, ProductAvailability, Store

# ---------------------------------------------------------------------------
# pytest-asyncio configuration
# ---------------------------------------------------------------------------
pytest_plugins = ("pytest_asyncio",)


# ---------------------------------------------------------------------------
# In-memory SQLite engine (shared across one test session)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


# ---------------------------------------------------------------------------
# Mock Kafka producer
# ---------------------------------------------------------------------------
class FakeKafkaProducer:
    """A lightweight mock that records every event sent through it."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def start(self) -> None:  # noqa: D401
        pass

    async def stop(self) -> None:
        pass

    async def send_event(self, topic: str, event_data: dict) -> None:
        self.events.append({"topic": topic, "data": event_data})

    def clear(self) -> None:
        self.events.clear()


fake_kafka = FakeKafkaProducer()


# ---------------------------------------------------------------------------
# Database dependency override
# ---------------------------------------------------------------------------
async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(autouse=True)
async def _setup_database():
    """Create all tables before each test and drop them afterwards."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    fake_kafka.clear()


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an ``httpx.AsyncClient`` wired to the FastAPI application."""
    # Override dependencies
    app.dependency_overrides[get_db] = _override_get_db

    # Monkey-patch the module-level kafka_producer used by the routers
    import app.routers.products as products_mod

    original_producer = products_mod.kafka_producer
    products_mod.kafka_producer = fake_kafka

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    # Restore
    products_mod.kafka_producer = original_producer
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed-data helpers
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def sample_category() -> Category:
    """Insert and return a sample category."""
    async with TestSessionLocal() as session:
        cat = Category(name="Roses", description="Beautiful roses")
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
        return cat


@pytest_asyncio.fixture()
async def sample_product(sample_category: Category) -> Product:
    """Insert and return a sample product (depends on ``sample_category``)."""
    async with TestSessionLocal() as session:
        prod = Product(
            name="Red Rose Bouquet",
            description="A dozen red roses",
            price=29.99,
            image_url="https://example.com/roses.jpg",
            category_id=sample_category.id,
        )
        session.add(prod)
        await session.commit()
        await session.refresh(prod)
        return prod


@pytest_asyncio.fixture()
async def sample_store() -> Store:
    """Insert and return a sample store."""
    async with TestSessionLocal() as session:
        store = Store(
            name="Downtown Flowers",
            address="123 Main St",
            latitude=55.7558,
            longitude=37.6173,
            phone="+1-555-0100",
        )
        session.add(store)
        await session.commit()
        await session.refresh(store)
        return store


@pytest_asyncio.fixture()
async def sample_availability(
    sample_product: Product, sample_store: Store
) -> ProductAvailability:
    """Insert and return a product-availability record."""
    async with TestSessionLocal() as session:
        avail = ProductAvailability(
            product_id=sample_product.id,
            store_id=sample_store.id,
            quantity=10,
        )
        session.add(avail)
        await session.commit()
        await session.refresh(avail)
        return avail
