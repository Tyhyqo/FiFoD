import logging

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import settings
from app.core.logging_config import setup_logging
from app.core.rate_limit import limiter
from app.infrastructure.lifespan import lifespan
from app.router import register_exception_handlers, register_routers

setup_logging(level=settings.LOG_LEVEL)

app = FastAPI(
    title="FiFoD — Files For Device",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

register_routers(app)
register_exception_handlers(app)


logger = logging.getLogger(__name__)


@app.get("/health", include_in_schema=False)
async def healthcheck():
    try:
        async with app.state.db_sessionmaker() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check failed: database unavailable")
        return {"status": "unhealthy", "database": "unavailable"}
    return {"status": "ok", "database": "available"}
