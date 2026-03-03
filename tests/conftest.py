import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import User
from app.db.session import get_session
from app.dependencies import get_current_user, get_http_client
from app.main import app
from app.services.auth_service import pwd_context

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL)

    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_conn, connection_record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    # SQLite не хранит timezone — приводим naive datetime к UTC при загрузке из БД
    from app.db.models import RefreshToken

    @event.listens_for(RefreshToken, "load")
    def _fix_refresh_token_tz(target, context):
        if target.expires_at and target.expires_at.tzinfo is None:
            target.expires_at = target.expires_at.replace(tzinfo=timezone.utc)

    async with engine.begin() as conn:
        # SQLite не поддерживает ARRAY — создаём только таблицы без этого типа
        tables = [
            t for t in Base.metadata.sorted_tables
            if t.name not in ("attachments", "attachment_files")
        ]
        await conn.run_sync(Base.metadata.create_all, tables=tables)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with sessionmaker() as session:
            yield session

    mock_http = AsyncMock()
    test_user = User(
        id=uuid.uuid4(),
        username="testuser",
        hashed_password=pwd_context.hash("testpass"),
        created_at=datetime.now(timezone.utc),
    )

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_http_client] = lambda: mock_http
    app.dependency_overrides[get_current_user] = lambda: test_user

    # healthcheck использует app.state.db_sessionmaker напрямую
    app.state.db_sessionmaker = sessionmaker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(engine, db_session) -> AsyncGenerator[AsyncClient, None]:
    """Клиент без переопределения get_current_user — для тестов авторизации."""
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with sessionmaker() as session:
            yield session

    mock_http = AsyncMock()

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_http_client] = lambda: mock_http
    app.state.db_sessionmaker = sessionmaker

    # Сбрасываем rate limiter для тестов
    from app.core.rate_limit import limiter
    app.state.limiter = limiter
    limiter.enabled = False

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    limiter.enabled = True
    app.dependency_overrides.clear()
