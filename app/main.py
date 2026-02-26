from fastapi import FastAPI

from app.config import settings
from app.core.logging_config import setup_logging
from app.infrastructure.lifespan import lifespan
from app.router import register_exception_handlers, register_routers

setup_logging(level=settings.LOG_LEVEL)

app = FastAPI(
    title="FiFoD — Files For Device",
    version="0.1.0",
    lifespan=lifespan,
)

register_routers(app)
register_exception_handlers(app)


@app.get("/health", include_in_schema=False)
def healthcheck():
    return {"status": "ok"}
