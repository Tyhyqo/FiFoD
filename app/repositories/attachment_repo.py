import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Attachment, AttachmentFile

logger = logging.getLogger(__name__)


class AttachmentRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, device_id: str, file_names: list[str]) -> Attachment:
        attachment = Attachment(device_id=device_id)
        self._session.add(attachment)
        # flush фиксирует attachment.id в БД до вставки дочерних записей (FK-ограничение)
        await self._session.flush()

        for name in file_names:
            self._session.add(
                AttachmentFile(
                    attachment_id=attachment.id,
                    file_name=name,
                )
            )

        await self._session.commit()
        logger.debug("Attachment committed: id=%s device=%s files=%s", attachment.id, device_id, file_names)

        # Перезагружаем объект с relation: в async SQLAlchemy lazy load недоступен вне
        # контекста IO — selectinload обязателен для доступа к files после commit.
        result = await self._session.execute(
            select(Attachment)
            .where(Attachment.id == attachment.id)
            .options(selectinload(Attachment.files))
        )
        return result.scalar_one()

    async def get_all(self) -> list[Attachment]:
        """Получить все привязки вместе с файлами."""
        result = await self._session.execute(
            select(Attachment).options(selectinload(Attachment.files))
        )
        attachments = list(result.scalars().all())
        logger.debug("Fetched %d attachments from DB.", len(attachments))
        return attachments
