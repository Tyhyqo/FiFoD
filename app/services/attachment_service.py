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

    async def create(self, device_id: str, file_names: list[str]) -> Attachment:
        """
        Создать привязку устройства к файлам.

        Проверяет, что устройство присутствует в списке свободных устройств
        внешнего API и что все указанные файлы существуют в директории.

        Raises:
            ExternalAPIError: если внешний API недоступен.
            DeviceNotFoundError: если устройство не найдено или не свободно.
            FilesNotFoundError: если один или несколько файлов отсутствуют.
        """
        logger.info("Creating attachment: device=%s files=%s", device_id, file_names)

        devices = await self._device_service.get_free_devices()
        available_serials = {d["serial"] for d in devices if d.get("serial")}

        if device_id not in available_serials:
            raise DeviceNotFoundError(
                f"Устройство '{device_id}' не найдено или недоступно."
            )

        # Убираем дубликаты, сохраняя оригинальный порядок (dict.fromkeys — O(n), Python 3.7+)
        unique_names = list(dict.fromkeys(file_names))

        missing = [f for f in unique_names if not await self._file_service.file_exists(f)]
        if missing:
            raise FilesNotFoundError(missing)

        attachment = await self._repo.create(device_id, unique_names)
        logger.info("Attachment created: id=%s device=%s", attachment.id, device_id)
        return attachment

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Attachment]:
        return await self._repo.get_all(skip=skip, limit=limit)
