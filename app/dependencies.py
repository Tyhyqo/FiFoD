import uuid

import httpx
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_session
from app.exceptions import InvalidCredentialsError
from app.repositories.attachment_repo import AttachmentRepo
from app.repositories.user_repo import UserRepo
from app.services.attachment_service import AttachmentService
from app.services.auth_service import AuthService
from app.services.device_service import DeviceService
from app.services.file_service import FileService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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


def get_user_repo(
    session: AsyncSession = Depends(get_session),
) -> UserRepo:
    return UserRepo(session)


def get_auth_service(
    repo: UserRepo = Depends(get_user_repo),
) -> AuthService:
    return AuthService(repo)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    repo: UserRepo = Depends(get_user_repo),
) -> User:
    payload = AuthService.decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidCredentialsError("Invalid access token.")

    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user:
        raise InvalidCredentialsError("User not found.")

    return user
