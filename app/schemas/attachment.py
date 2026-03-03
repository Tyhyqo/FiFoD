import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class AttachmentCreateIn(BaseModel):
    deviceId: str = Field(min_length=1)
    # Field(min_length=1) на list — список непустой;
    # Annotated[str, Field(min_length=1)] — каждое имя файла непустое
    fileNames: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)
    comment: str | None = None
    tags: list[str] = Field(default_factory=list)


class AttachmentFileOut(BaseModel):
    id: uuid.UUID
    file_name: str

    model_config = {"from_attributes": True}


class AttachmentOut(BaseModel):
    id: uuid.UUID
    device_id: str
    comment: str | None
    tags: list[str]
    created_at: datetime
    files: list[AttachmentFileOut]

    model_config = {"from_attributes": True}
