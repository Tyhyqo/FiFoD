import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.database import create_engine, create_sessionmaker
from app.infrastructure.http_client import create_http_client
from app.repositories.user_repo import UserRepo

logger = logging.getLogger(__name__)


async def _cleanup_expired_tokens(sessionmaker) -> None:
    """Фоновая задача: раз в час удаляет просроченные refresh-токены."""
    while True:
        await asyncio.sleep(3600)
        try:
            async with sessionmaker() as session:
                repo = UserRepo(session)
                await repo.delete_expired_refresh_tokens()
                logger.info("Expired refresh tokens cleaned up.")
        except Exception:
            logger.exception("Error cleaning up expired tokens.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: инициализация пула соединений с БД и HTTP-клиента.
    Shutdown: корректное освобождение всех ресурсов.
    """
    engine = create_engine()
    app.state.db_engine = engine
    app.state.db_sessionmaker = create_sessionmaker(engine)
    app.state.http_client = create_http_client()

    cleanup_task = asyncio.create_task(_cleanup_expired_tokens(app.state.db_sessionmaker))
    logger.info("Infrastructure initialized.")
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

        # Каждый ресурс закрывается независимо: сбой одного не блокирует остальные.
        logger.info("Graceful shutdown: releasing infrastructure resources...")
        try:
            await app.state.http_client.aclose()
            logger.info("HTTP client closed.")
        except Exception:
            logger.exception("Error closing HTTP client.")

        try:
            await app.state.db_engine.dispose()
            logger.info("DB engine disposed.")
        except Exception:
            logger.exception("Error disposing DB engine.")
