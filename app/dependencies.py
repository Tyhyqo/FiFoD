import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.attachment_repo import AttachmentRepo
from app.services.attachment_service import AttachmentService
from app.services.device_service import DeviceService
from app.services.file_service import FileService


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_device_service(
    client: httpx.AsyncClient = Depends(get_http_client),
) -> DeviceService:
    return DeviceService(client)


def get_file_service() -> FileService:
    return FileService()


def get_attachment_repo(
    session: AsyncSession = Depends(get_session),
) -> AttachmentRepo:
    return AttachmentRepo(session)


def get_attachment_service(
    repo: AttachmentRepo = Depends(get_attachment_repo),
    device_service: DeviceService = Depends(get_device_service),
    file_service: FileService = Depends(get_file_service),
) -> AttachmentService:
    return AttachmentService(repo, device_service, file_service)
