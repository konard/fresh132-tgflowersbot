"""Shared fixtures for order-service tests.

Uses an in-memory SQLite database (via aiosqlite) so that no external
services are required, and mocks the Kafka producer so events are silently
discarded.
"""

from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.models import Cart, Order

# ---------------------------------------------------------------------------
# SQLite compatibility: enable eager_defaults so that server-generated
# columns (e.g. ``updated_at`` with ``onupdate=func.now()``) are fetched
# immediately after INSERT / UPDATE instead of triggering an implicit
# lazy-load that would fail outside the async greenlet context.
# ---------------------------------------------------------------------------

for _model in (Order, Cart):
    _model.__mapper__.eager_defaults = True

# ---------------------------------------------------------------------------
# In-memory SQLite engine shared across the test session
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Dependency override: provide test DB sessions to the FastAPI app
# ---------------------------------------------------------------------------

async def _override_get_session():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_session] = _override_get_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def _setup_database():
    """Create all tables before each test and drop them afterwards.

    This gives every test a clean database.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """Provide an ``httpx.AsyncClient`` wired to the FastAPI app.

    The Kafka ``send_event`` function is patched to a no-op ``AsyncMock``
    so that tests never attempt a real Kafka connection.
    """
    with patch("app.routers.orders.send_event", new_callable=AsyncMock):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
