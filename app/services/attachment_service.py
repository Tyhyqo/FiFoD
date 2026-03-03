import asyncio
import logging

from app.db.models import Attachment
from app.exceptions import DeviceNotFoundError, FilesNotFoundError
from app.repositories.attachment_repo import AttachmentRepo
from app.services.device_service import DeviceService
from app.services.file_service import FileService

logger = logging.getLogger(__name__)


class AttachmentService:

    def __init__(
        self,
        repo: AttachmentRepo,
        device_service: DeviceService,
        file_service: FileService,
    ) -> None:
        self._repo = repo
        self._device_service = device_service
        self._file_service = file_service

    async def create(
        self,
        device_id: str,
        file_names: list[str],
        comment: str | None = None,
        tags: list[str] | None = None,
    ) -> Attachment:
        """Создать привязку устройства к файлам, проверив доступность устройства и наличие файлов."""
        logger.info("Creating attachment: device=%s files=%s", device_id, file_names)

        devices = await self._device_service.get_free_devices()
        available_serials = {d["serial"] for d in devices if d.get("serial")}

        if device_id not in available_serials:
            raise DeviceNotFoundError(
                f"Device '{device_id}' not found or unavailable."
            )

        unique_names = list(dict.fromkeys(file_names))

        checks = await asyncio.gather(
            *(self._file_service.file_exists(name) for name in unique_names)
        )
        missing = [name for name, exists in zip(unique_names, checks) if not exists]
        if missing:
            raise FilesNotFoundError(missing)

        attachment = await self._repo.create(device_id, unique_names, comment=comment, tags=tags)
        logger.info("Attachment created: id=%s device=%s", attachment.id, device_id)
        return attachment

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        tags: list[str] | None = None,
    ) -> list[Attachment]:
        return await self._repo.get_all(skip=skip, limit=limit, tags=tags)
