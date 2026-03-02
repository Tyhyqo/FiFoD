import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.exceptions import (
    DeviceNotFoundError,
    ExternalAPIError,
    FilesNotFoundError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
)

logger = logging.getLogger(__name__)


async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.debug(
        "Request validation error: %s %s — %s",
        request.method,
        request.url,
        exc.errors(),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


async def external_api_error_handler(
    request: Request, exc: ExternalAPIError
) -> JSONResponse:
    logger.warning("External API error: %s %s — %s", request.method, request.url, exc)
    return JSONResponse(status_code=503, content={"detail": str(exc)})


async def device_not_found_handler(
    request: Request, exc: DeviceNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def files_not_found_handler(
    request: Request, exc: FilesNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Files not found in working directory.", "missing": exc.missing},
    )


async def db_operational_error_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    logger.error(
        "Database operational error on %s %s",
        request.method,
        request.url,
        exc_info=True,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable."},
    )


async def invalid_credentials_handler(
    request: Request, exc: InvalidCredentialsError
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def user_already_exists_handler(
    request: Request, exc: UserAlreadyExistsError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def invalid_refresh_token_handler(
    request: Request, exc: InvalidRefreshTokenError
) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception("Unhandled exception: %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )
