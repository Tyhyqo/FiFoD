import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Attachment, AttachmentFile

logger = logging.getLogger(__name__)


class AttachmentRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        device_id: str,
        file_names: list[str],
        comment: str | None = None,
        tags: list[str] | None = None,
    ) -> Attachment:
        attachment = Attachment(
            device_id=device_id,
            comment=comment,
            tags=tags or [],
        )
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

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        tags: list[str] | None = None,
    ) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .options(selectinload(Attachment.files))
            .order_by(Attachment.created_at.desc())
        )

        if tags:
            for tag in tags:
                stmt = stmt.where(Attachment.tags.contains([tag]))

        stmt = stmt.offset(skip).limit(limit)

        result = await self._session.execute(stmt)
        attachments = list(result.scalars().all())
        logger.debug("Fetched %d attachments from DB.", len(attachments))
        return attachments
