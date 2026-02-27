from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import OperationalError

from app.api.attachments import router as attachments_router
from app.api.devices import router as devices_router
from app.api.exception_handlers import (
    db_operational_error_handler,
    device_not_found_handler,
    external_api_error_handler,
    files_not_found_handler,
    request_validation_error_handler,
    unhandled_exception_handler,
)
from app.api.files import router as files_router
from app.exceptions import DeviceNotFoundError, ExternalAPIError, FilesNotFoundError


def register_routers(app: FastAPI) -> None:
    app.include_router(devices_router, prefix="/api", tags=["Устройства"])
    app.include_router(files_router, prefix="/api", tags=["Файлы"])
    app.include_router(attachments_router, prefix="/api", tags=["Привязки"])


def register_exception_handlers(app: FastAPI) -> None:
    """Порядок регистрации важен: специфичные типы до Exception."""
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(OperationalError, db_operational_error_handler)
    app.add_exception_handler(ExternalAPIError, external_api_error_handler)
    app.add_exception_handler(DeviceNotFoundError, device_not_found_handler)
    app.add_exception_handler(FilesNotFoundError, files_not_found_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
