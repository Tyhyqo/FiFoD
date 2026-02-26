import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    files: Mapped[list["AttachmentFile"]] = relationship(
        back_populates="attachment", cascade="all, delete-orphan"
    )


class AttachmentFile(Base):
    __tablename__ = "attachment_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE")
    )
    file_name: Mapped[str] = mapped_column()

    attachment: Mapped["Attachment"] = relationship(back_populates="files")
