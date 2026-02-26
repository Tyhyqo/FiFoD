import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.database import create_engine, create_sessionmaker
from app.infrastructure.http_client import create_http_client

logger = logging.getLogger(__name__)


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
    logger.info("Infrastructure initialized.")
    try:
        yield
    finally:
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
